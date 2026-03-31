import os
import sys
import pytest
from unittest.mock import MagicMock
from langchain_core.documents import Document

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag_system.indexer import DocumentIndexer

@pytest.fixture
def mock_indexer(tmp_path):
    # Mock HuggingFaceEmbeddings to avoid model download
    with MagicMock() as mock_embed:
        from unittest.mock import patch
        with patch('rag_system.indexer.HuggingFaceEmbeddings', return_value=mock_embed):
            docs_dir = tmp_path / "docs"
            docs_dir.mkdir()
            persist_dir = tmp_path / "chroma"
            return DocumentIndexer(documents_dir=str(docs_dir), persist_dir=str(persist_dir))

def test_split_documents(mock_indexer):
    # 构造两条伪造的 document
    doc1 = Document(
        page_content="这是一个测试文档。" * 50, # 足够长以触发分块
        metadata={"source": "/tmp/test1.txt"}
    )
    doc2 = Document(
        page_content="另外一个测试长文档" * 60,
        metadata={"source": "/tmp/test2.pdf", "page": 5}
    )
    
    chunks = mock_indexer.split_documents([doc1, doc2])
    
    # 验证分块数量（大于原文档）
    assert len(chunks) > 2
    
    # 验证 metadata 完整性
    for idx, chunk in enumerate(chunks):
        assert "source" in chunk.metadata
        # 路径应被处理为 basename
        assert chunk.metadata["source"] in ["test1.txt", "test2.pdf"]
        assert "chunk_id" in chunk.metadata
        assert "page" in chunk.metadata
        
        # 验证默认页码处理
        if chunk.metadata["source"] == "test1.txt":
            assert chunk.metadata["page"] == -1
        else:
            assert chunk.metadata["page"] == 5

def test_load_documents_empty(mock_indexer):
    docs = mock_indexer.load_documents()
    assert len(docs) == 0
