"""
config.py - 全局配置与 LLM 初始化
知识点:
  - ChatOpenAI 兼容 DeepSeek API（base_url 替换）
  - python-dotenv 环境变量管理
  - Pydantic Settings 风格的常量定义
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 自动查找项目根目录的 .env
_root = Path(__file__).parent.parent
load_dotenv(_root / ".env")

# ── LLM 参数 ────────────────────────────────────────────────
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# ── 执行参数 ─────────────────────────────────────────────────
RETRY_MAX_TIMES: int = int(os.getenv("RETRY_MAX_TIMES", "3"))
PARALLEL_WORKERS: int = int(os.getenv("PARALLEL_WORKERS", "3"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


def get_llm(temperature: float = 0.3):
    """
    返回指向 DeepSeek 服务的 ChatOpenAI 实例。
    DeepSeek 完全兼容 OpenAI 接口规范，只需替换 base_url 与 api_key。
    """
    from langchain_openai import ChatOpenAI

    if not DEEPSEEK_API_KEY:
        raise EnvironmentError(
            "DEEPSEEK_API_KEY 未设置，请在项目根目录创建 .env 文件，"
            "参考 .env.example 填写您的密钥。"
        )

    return ChatOpenAI(
        model=DEEPSEEK_MODEL,
        openai_api_key=DEEPSEEK_API_KEY,
        openai_api_base=DEEPSEEK_BASE_URL,
        temperature=temperature,
        max_retries=RETRY_MAX_TIMES,
    )
