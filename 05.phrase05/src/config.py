"""
config.py - 全局配置管理
知识点: 使用 python-dotenv 加载环境变量，通过 Pydantic BaseSettings 统一管理
生产级实践: 所有配置集中化，防止硬编码；字段有默认值和类型校验
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 自动加载项目根目录的 .env 文件
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)


class Config:
    """全局配置类 - 从环境变量读取所有配置"""

    # --- DeepSeek LLM ---
    DEEPSEEK_API_KEY: str = os.environ.get("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL: str = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    # --- 审核业务逻辑阈值 ---
    # AI 置信度高于此值时，直接自动通过，无需人工干预
    CONFIDENCE_THRESHOLD: float = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.8"))
    # 允许进入 human_review 节点的最大次数，超出后路由至兜底节点
    MAX_REVIEW_LOOPS: int = int(os.environ.get("MAX_REVIEW_LOOPS", "3"))


settings = Config()
