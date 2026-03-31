import os
import glob
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    DOCUMENTS_DIR,
    CHROMA_PERSIST_DIR,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    EMBEDDING_MODEL,
    EMBEDDING_DEVICE
)

class DocumentIndexer:
    """文档加载与索引构建器"""

    def __init__(self, documents_dir: str = DOCUMENTS_DIR, persist_dir: str = CHROMA_PERSIST_DIR):
        self.documents_dir = documents_dir
        self.persist_dir = persist_dir
        
        # 初始化分块器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", ".", " ", ""]
        )
        
        # 初始化 Embedding 模型 (本地)
        self.embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={'device': EMBEDDING_DEVICE}
        )
        
    def load_documents(self) -> List[Document]:
        """加载 documents 目录下的所有支持的文件（TXT, PDF）"""
        if not os.path.exists(self.documents_dir):
            os.makedirs(self.documents_dir)
            
        docs = []
        # 处理 txt 文件
        for txt_file in glob.glob(os.path.join(self.documents_dir, "*.txt")):
            loader = TextLoader(txt_file, encoding="utf-8")
            docs.extend(loader.load())
            
        # 处理 pdf 文件
        for pdf_file in glob.glob(os.path.join(self.documents_dir, "*.pdf")):
            loader = PyPDFLoader(pdf_file)
            docs.extend(loader.load())
            
        return docs

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """对文档进行分块，并附加额外的 metadata"""
        chunks = self.text_splitter.split_documents(documents)
        
        # 补充 metadata: source_file, chunk_id, page
        for i, chunk in enumerate(chunks):
            source = chunk.metadata.get("source", "unknown")
            # 简化 source 路径为文件名
            chunk.metadata["source"] = os.path.basename(source)
            chunk.metadata["chunk_id"] = f"{os.path.basename(source)}_chunk_{i}"
            if "page" not in chunk.metadata:
                chunk.metadata["page"] = -1  # 默认无页码
                
        return chunks

    def build_index(self) -> Chroma:
        """完整管线：加载 -> 分块 -> 写入 Chroma 向量数据库"""
        print(f"Loading documents from {self.documents_dir}...")
        raw_docs = self.load_documents()
        
        if not raw_docs:
            print("No documents found to index.")
            # 返回一个空的 DB（如果存在会加载现有的）
            return Chroma(persist_directory=self.persist_dir, embedding_function=self.embeddings)
            
        print(f"Splitting {len(raw_docs)} documents...")
        chunks = self.split_documents(raw_docs)
        print(f"Generated {len(chunks)} chunks. Building vector index at {self.persist_dir}...")
        
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=self.persist_dir
        )
        print("Index building completed.")
        return vectorstore

if __name__ == "__main__":
    indexer = DocumentIndexer()
    indexer.build_index()
