import os
from dotenv import load_dotenv

load_dotenv()

# LLM 配置
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
# EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")

# 检索与分块配置
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
RETRIEVER_TOP_K = int(os.getenv("RETRIEVER_TOP_K", "4"))
RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", "0.3"))

# 记忆配置
MEMORY_WINDOW_SIZE = int(os.getenv("MEMORY_WINDOW_SIZE", "10"))

# 向量存储配置
VECTOR_STORE_TYPE = "chroma"
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
DOCUMENTS_DIR = os.path.join(os.path.dirname(__file__), "documents")
