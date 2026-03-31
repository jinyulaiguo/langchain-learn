import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag_system.models import RouteDecision, RetrievalResult, RetrievedDocument
from rag_system.memory import ConversationMemory
from rag_system.router import Router
from rag_system.formatter import ResponseFormatter
from unittest.mock import MagicMock

def test_integration_routing_and_memory_isolation():
    """
    测试场景 1：记忆与检索隔离验证
    """
    memory = ConversationMemory(window_size=2)
    mock_retriever = MagicMock()
    router = Router(retriever=mock_retriever)
    
    # === 轮次 1：检索问题 ===
    # 构造假检索结果
    mock_result = RetrievalResult(
        query="什么是 RAG？",
        total_retrieved=3,
        filtered_count=1,
        documents=[RetrievedDocument(content="RAG 结合了检索和生成。", score=0.85, source="test.txt", chunk_id="1")]
    )
    mock_retriever.retrieve.return_value = mock_result
    
    # 模拟路由
    decision1 = router.determine_path("什么是 RAG？")
    assert decision1.path == "retrieval"
    
    # 模拟 Chain 生成
    answer1 = "根据文档，RAG 结合了检索和生成。"
    
    # 存入记忆（隔离测试：确保存入的仅为结果的纯文本，不包含文档本身）
    memory.add_turn("什么是 RAG？", answer1)
    
    history1 = memory.get_history()
    # 记忆中不包含文档的 source 字段 "test.txt" 或者 metadata 内容
    assert "test.txt" not in history1
    assert "chunk_id" not in history1
    assert answer1 in history1
    
    # === 轮次 2：记忆问题 ===
    # 重置 mock，确保走记忆路径不触发 retrieve
    mock_retriever.retrieve.reset_mock()
    decision2 = router.determine_path("你刚才说什么？")
    
    assert decision2.path == "memory"
    mock_retriever.retrieve.assert_not_called()
    
    answer2 = "我刚才说 RAG 结合了检索和生成。"
    memory.add_turn("你刚才说什么？", answer2)
    
    history2 = memory.get_history()
    assert answer2 in history2

def test_integration_formatter():
    """测试场景 2: 来源引用暴露功能"""
    mock_result = RetrievalResult(
        query="LangChain 有哪些 Memory？",
        total_retrieved=4,
        filtered_count=2,
        documents=[
            RetrievedDocument(content="包含 ConversationBufferMemory 等", score=0.9123, source="doc.pdf", page=5, chunk_id="chk_2"),
            RetrievedDocument(content="还包含 WindowMemory", score=0.8844, source="doc.txt", page=-1, chunk_id="chk_3")
        ]
    )
    decision = RouteDecision(
        path="retrieval", 
        reason="检索通过", 
        retrieval_result=mock_result
    )
    
    raw_ans = "LangChain 有 BufferMemory 和 WindowMemory。"
    final_output = ResponseFormatter.format(raw_ans, decision)
    
    # 验证关键内容展示在输出中
    assert "📝 回答：\nLangChain" in final_output
    assert "📂 回答路径：检索路径 (Retrieval Path)" in final_output
    assert "  - 初始召回数量：4" in final_output
    assert "  - 过滤后剩余数：2" in final_output
    assert "  - Top-1 分数：0.9123" in final_output
    
    # 验证引用存在
    assert "[1] doc.pdf | 页码: 5 | Chunk ID: chk_2 | 分数: 0.9123" in final_output
    assert "[2] doc.txt | Chunk ID: chk_3 | 分数: 0.8844" in final_output
    # 且页码为 -1 的 txt 文档被正确隐藏页码显示
    assert "页码: -1" not in final_output
