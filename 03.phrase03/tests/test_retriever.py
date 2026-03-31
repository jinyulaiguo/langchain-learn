import os
import sys
import pytest
from unittest.mock import MagicMock
from langchain_core.documents import Document

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag_system.retriever import RetrieverWrapper
from rag_system.models import RetrievalResult

@pytest.fixture
def mock_retriever():
    from unittest.mock import patch
    with patch('rag_system.retriever.HuggingFaceEmbeddings', return_value=MagicMock()):
        with patch('rag_system.retriever.Chroma', return_value=MagicMock()):
            retriever = RetrieverWrapper(persist_dir="dummy")
            # 替换内部 vectorstore 的检索方法进行 Mock 测试
            mock_vectorstore = MagicMock()
    
    # 构建假结果：(Document, score)
    fake_docs_with_scores = [
        (Document(page_content="High relevant doc", metadata={"source": "test.txt", "chunk_id": "1", "page": 1}), 0.85),
        (Document(page_content="Medium relevant doc", metadata={"source": "test.txt", "chunk_id": "2", "page": 1}), 0.45),
        (Document(page_content="Low relevant doc", metadata={"source": "test.txt", "chunk_id": "3", "page": -1}), 0.15),
    ]
    
    mock_vectorstore.similarity_search_with_relevance_scores.return_value = fake_docs_with_scores
    retriever.vectorstore = mock_vectorstore
    return retriever

def test_retriever_filtering(mock_retriever):
    # 设定阈值为 0.3
    result = mock_retriever.retrieve("What is this?", top_k=3, threshold=0.3)
    
    assert isinstance(result, RetrievalResult)
    assert result.total_retrieved == 3
    assert result.filtered_count == 2
    assert len(result.documents) == 2
    
    # 验证是否只保留了 >= 0.3 的文档
    assert result.documents[0].score == 0.85
    assert result.documents[1].score == 0.45
    
    # 验证 Document -> RetrievedDocument 转换映射
    assert result.documents[0].content == "High relevant doc"
    assert result.documents[0].source == "test.txt"
    assert result.documents[0].chunk_id == "1"
    assert result.documents[0].page == 1

def test_retriever_all_filtered(mock_retriever):
    # 设定阈值为 0.9，所有假结果都低于此值
    result = mock_retriever.retrieve("What is this?", top_k=3, threshold=0.9)
    
    assert result.total_retrieved == 3
    assert result.filtered_count == 0
    assert len(result.documents) == 0
