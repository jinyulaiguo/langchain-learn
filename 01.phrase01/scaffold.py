import sys
from pathlib import Path

# 定义你的包名（注意：Python 包名必须使用下划线，不能用横杠）
PACKAGE_NAME = "lang_series_project"

# 定义目录结构
DIRECTORIES = [
    f"src/{PACKAGE_NAME}/api/routes",
    f"src/{PACKAGE_NAME}/core",
    f"src/{PACKAGE_NAME}/agents",
    f"src/{PACKAGE_NAME}/services",
    f"src/{PACKAGE_NAME}/models",
    f"src/{PACKAGE_NAME}/utils",
    "tests/test_api",
    "tests/test_agents",
]

# 定义需要创建的文件及其初始样板代码
FILES_WITH_CONTENT = {
    ".env": "DEEPSEEK_API_KEY=your_api_key_here\n",
    ".env.example": "DEEPSEEK_API_KEY=\n",
    f"src/{PACKAGE_NAME}/__init__.py": "",
    
    # Core 配置样板代码
    f"src/{PACKAGE_NAME}/core/config.py": f"""from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    project_name: str = "DeepSeek AI Agent Service"
    deepseek_api_key: str = ""
    deepseek_api_base: str = "https://api.deepseek.com/v1"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
""",
    f"src/{PACKAGE_NAME}/core/exceptions.py": "# 全局异常定义\n",
    f"src/{PACKAGE_NAME}/core/__init__.py": "",

    # API 样板代码
    f"src/{PACKAGE_NAME}/api/dependencies.py": "# FastAPI 依赖注入\n",
    f"src/{PACKAGE_NAME}/api/routes/chat.py": "# 对话路由\n",
    f"src/{PACKAGE_NAME}/api/routes/__init__.py": "",
    f"src/{PACKAGE_NAME}/api/__init__.py": "",

    # Agents 样板代码
    f"src/{PACKAGE_NAME}/agents/llm.py": f"""from langchain_openai import ChatOpenAI
from {PACKAGE_NAME}.core.config import settings

def get_deepseek_llm(temperature: float = 0.7):
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_api_base,
        max_tokens=4096,
        temperature=temperature
    )
""",
    f"src/{PACKAGE_NAME}/agents/state.py": "from typing import TypedDict, Annotated\nimport operator\n\nclass AgentState(TypedDict):\n    messages: Annotated[list, operator.add]\n",
    f"src/{PACKAGE_NAME}/agents/nodes.py": "# 图节点定义\n",
    f"src/{PACKAGE_NAME}/agents/tools.py": "# 工具定义 (Function Calling)\n",
    f"src/{PACKAGE_NAME}/agents/graph.py": "# 图编排逻辑\n",
    f"src/{PACKAGE_NAME}/agents/__init__.py": "",

    # 其他层
    f"src/{PACKAGE_NAME}/services/user_service.py": "",
    f"src/{PACKAGE_NAME}/services/__init__.py": "",
    f"src/{PACKAGE_NAME}/models/domain.py": "# 数据库模型\n",
    f"src/{PACKAGE_NAME}/models/schemas.py": "# Pydantic 接口验证模型\n",
    f"src/{PACKAGE_NAME}/models/__init__.py": "",
    f"src/{PACKAGE_NAME}/utils/logger.py": "# 日志配置\n",
    f"src/{PACKAGE_NAME}/utils/__init__.py": "",
    
    # 测试文件
    "tests/conftest.py": "# Pytest fixtures\n",
    "tests/__init__.py": "",
}

def create_structure():
    print("🚀 开始构建生产级目录结构...")
    
    # 1. 创建目录
    for dir_path in DIRECTORIES:
        path = Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        print(f"📁 Created directory: {path}")

    # 2. 创建文件并写入内容
    for file_path, content in FILES_WITH_CONTENT.items():
        path = Path(file_path)
        # 如果文件已存在，不覆盖（保护你可能已经写好的代码）
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"📄 Created file: {path}")
        else:
            print(f"⚠️ Skipped existing file: {path}")

    print("✅ 目录骨架搭建完成！")
    print("💡 提示: 搭建完成后，你可以删除这个 scaffold.py 脚本。")

if __name__ == "__main__":
    create_structure()