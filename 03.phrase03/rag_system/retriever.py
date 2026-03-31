import os
import sys

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    CHROMA_PERSIST_DIR, 
    RETRIEVER_TOP_K, 
    RELEVANCE_THRESHOLD, 
    EMBEDDING_MODEL,
    EMBEDDING_DEVICE
)
from rag_system.models import RetrievalResult, RetrievedDocument

class RetrieverWrapper:
    """检索器封装，提供召回、评分与过滤"""
    
    def __init__(self, persist_dir: str = CHROMA_PERSIST_DIR):
        self.embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={'device': EMBEDDING_DEVICE}
        )
        self.vectorstore = Chroma(
            persist_directory=persist_dir,
            embedding_function=self.embeddings
        )

    def retrieve(self, query: str, top_k: int = RETRIEVER_TOP_K, threshold: float = RELEVANCE_THRESHOLD) -> RetrievalResult:
        """
        根据 query 去向量库中检索相关文档，并进行相关性阈值过滤
        """
        # 注意: 对于 Chroma，默认 similarity_search_with_relevance_scores 会把距离转换为 [0, 1] 的分数
        # 考虑到可能没有初始化或者未支持 relevance fn 的情况，这里用 try-except 进行安全降级
        try:
            raw_results = self.vectorstore.similarity_search_with_relevance_scores(query, k=top_k)
        except Exception:
            # 降级：直接取 score（Chroma 默认返回 L2 distance, 越小越好），这里为了逻辑统一做个简单反转映射
            # 仅作为 fallback，实际上 OpenAI 向量是归一化的，L2 distance 范围是 [0, 2]
            dist_results = self.vectorstore.similarity_search_with_score(query, k=top_k)
            raw_results = [(doc, max(0.0, 1.0 - (dist / 2.0))) for doc, dist in dist_results]

        total_retrieved = len(raw_results)
        
        filtered_docs = []
        for doc, score in raw_results:
            if score >= threshold:
                retrieved_doc = RetrievedDocument(
                    content=doc.page_content,
                    score=float(score),
                    source=doc.metadata.get("source", "unknown"),
                    page=doc.metadata.get("page", None),
                    chunk_id=doc.metadata.get("chunk_id", "unknown")
                )
                filtered_docs.append(retrieved_doc)
                
        # 按分数降序排列
        filtered_docs.sort(key=lambda x: x.score, reverse=True)
        
        return RetrievalResult(
            query=query,
            total_retrieved=total_retrieved,
            filtered_count=len(filtered_docs),
            documents=filtered_docs
        )
