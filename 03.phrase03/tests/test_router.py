import os
import sys
import pytest
from unittest.mock import MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag_system.router import Router
from rag_system.models import RetrievalResult, RouteDecision, RetrievedDocument

@pytest.fixture
def mock_retriever():
    return MagicMock()

def test_router_explicit_command(mock_retriever):
    router = Router(retriever=mock_retriever)
    
    # 测试 /chat
    decision1 = router.determine_path("/chat What is this?")
    assert decision1.path == "memory"
    assert "指定 /chat" in decision1.reason
    
    # 测试 /search (模拟检索通过阈值)
    mock_result = RetrievalResult(
        query="What is this?",
        total_retrieved=3,
        filtered_count=1,
        documents=[
            RetrievedDocument(content="dummy", score=0.9, source="a.txt", chunk_id="1")
        ]
    )
    mock_retriever.retrieve.return_value = mock_result
    
    decision2 = router.determine_path("/search What is this?")
    assert decision2.path == "retrieval"
    assert "指定 /search" in decision2.reason
    assert decision2.retrieval_result == mock_result

def test_router_memory_keywords(mock_retriever):
    router = Router(retriever=mock_retriever)
    decision = router.determine_path("你刚才说的意思是？")
    assert decision.path == "memory"
    assert "匹配到上下文指代词" in decision.reason
    # 走记忆路径时，甚至不会触发检索
    mock_retriever.retrieve.assert_not_called()

def test_router_fallback_to_memory(mock_retriever):
    router = Router(retriever=mock_retriever)
    
    # 模拟检索失败（所有结果低于阈值）
    mock_result = RetrievalResult(
        query="Random question",
        total_retrieved=3,
        filtered_count=0,
        documents=[]
    )
    mock_retriever.retrieve.return_value = mock_result
    
    decision = router.determine_path("Random question")
    assert decision.path == "memory"
    assert "降级" in decision.reason
    # 但由于曾经尝试过检索，retrieval_result 将被保留下来以供日志追踪
    assert decision.retrieval_result == mock_result
