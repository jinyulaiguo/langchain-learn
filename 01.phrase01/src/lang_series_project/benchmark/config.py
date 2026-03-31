"""
配置管理模块 - DeepSeek 专版
修正了 .env 路径定位逻辑
"""
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


def _load_env_file(env_path: Path) -> None:
    """解析 .env 文件"""
    if not env_path.exists():
        # print(f"⚠️ 未找到 .env 文件: {env_path}", file=sys.stderr)
        return
    
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key not in os.environ:
                    os.environ[key] = value


# --- 修正路径计算 ---
# 当前文件: src/lang_series_project/benchmark/config.py
# parent[0]: benchmark/
# parent[1]: lang_series_project/
# parent[2]: src/
# parent[3]: 01.Phrase01/ (项目根目录)
_project_root = Path(__file__).parents[3]
_load_env_file(_project_root / ".env")


@dataclass
class DeepSeekConfig:
    """DeepSeek API 配置"""
    base_url: str = "https://api.deepseek.com/v1"
    api_key: str = ""
    model: str = "deepseek-chat"
    timeout: float = 60.0


@dataclass
class BenchmarkConfig:
    """基准测试全局配置"""
    test_prompt: str = "请用一句话解释什么是机器学习。"
    concurrent_requests: int = 3
    output_dir: Path = field(default_factory=lambda: Path("benchmark_results"))
    api: DeepSeekConfig = field(default_factory=DeepSeekConfig)


def load_config() -> BenchmarkConfig:
    """加载 DeepSeek 配置"""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    
    # 调试信息: 如果仍然报错，可以看到搜索路径
    if not api_key or api_key == "your_api_key_here":
        raise EnvironmentError(
            f"❌ 未找到有效的 DEEPSEEK_API_KEY！\n"
            f"   尝试搜索的 .env 路径为: {_project_root / '.env'}\n"
            f"   请检查该路径下是否存在密钥配置。"
        )

    return BenchmarkConfig(api=DeepSeekConfig(api_key=api_key))
