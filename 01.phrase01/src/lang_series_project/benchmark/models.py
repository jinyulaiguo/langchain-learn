"""
数据模型模块
定义基准测试结果的结构化数据类
使用 dataclass 避免 pydantic 依赖（验证原生 Python 能力）
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import json

from .errors import ErrorType


@dataclass
class TokenUsage:
    """Token 用量统计"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CallResult:
    """单次 API 调用结果"""
    provider: str                              # 提供商名称
    model: str                                 # 模型名称
    mode: str                                  # "sync" 或 "async"
    call_index: int                            # 调用序号（并发时使用）

    # 时间数据
    start_time: str = ""                       # ISO8601 格式
    end_time: str = ""
    latency_ms: float = 0.0                   # 响应延迟（毫秒）

    # 结果数据
    success: bool = False
    content: str = ""                          # LLM 返回内容
    token_usage: TokenUsage = field(default_factory=TokenUsage)

    # 错误信息（失败时填充）
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    status_code: Optional[int] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        # asdict 会自动递归处理嵌套 dataclass
        return d


@dataclass
class ProviderReport:
    """单个提供商的完整基准报告"""
    provider: str
    model: str
    sync_results: list[CallResult] = field(default_factory=list)
    async_results: list[CallResult] = field(default_factory=list)

    # 统计摘要 —— 在 finalize() 后填充
    sync_avg_latency_ms: float = 0.0
    async_avg_latency_ms: float = 0.0
    sync_success_rate: float = 0.0
    async_success_rate: float = 0.0
    speedup_ratio: float = 0.0              # 异步相对同步的加速比

    def finalize(self) -> None:
        """计算统计摘要"""
        def _avg_latency(results: list[CallResult]) -> float:
            successful = [r for r in results if r.success]
            if not successful:
                return 0.0
            return sum(r.latency_ms for r in successful) / len(successful)

        def _success_rate(results: list[CallResult]) -> float:
            if not results:
                return 0.0
            return sum(1 for r in results if r.success) / len(results)

        self.sync_avg_latency_ms = _avg_latency(self.sync_results)
        self.async_avg_latency_ms = _avg_latency(self.async_results)
        self.sync_success_rate = _success_rate(self.sync_results)
        self.async_success_rate = _success_rate(self.async_results)

        # 加速比：同步平均延迟 / 异步平均延迟（越大代表异步优势越明显）
        if self.async_avg_latency_ms > 0 and self.sync_avg_latency_ms > 0:
            self.speedup_ratio = round(
                self.sync_avg_latency_ms / self.async_avg_latency_ms, 2
            )

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "summary": {
                "sync_avg_latency_ms": round(self.sync_avg_latency_ms, 2),
                "async_avg_latency_ms": round(self.async_avg_latency_ms, 2),
                "sync_success_rate": round(self.sync_success_rate, 4),
                "async_success_rate": round(self.async_success_rate, 4),
                "speedup_ratio": self.speedup_ratio,
            },
            "sync_results": [r.to_dict() for r in self.sync_results],
            "async_results": [r.to_dict() for r in self.async_results],
        }


@dataclass
class BenchmarkReport:
    """完整的基准测试报告"""
    benchmark_id: str                           # 唯一标识
    created_at: str                             # 报告生成时间
    test_prompt: str                            # 测试使用的 prompt
    concurrent_requests: int                    # 异步并发数
    provider_reports: list[ProviderReport] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "benchmark_id": self.benchmark_id,
            "created_at": self.created_at,
            "test_prompt": self.test_prompt,
            "concurrent_requests": self.concurrent_requests,
            "providers": [p.to_dict() for p in self.provider_reports],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
