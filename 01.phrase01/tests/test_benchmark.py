"""
基准测试模块单元测试
测试错误分类、数据模型、配置加载等逻辑

运行方式：
    uv run python -m pytest tests/test_benchmark.py -v
"""
import pytest
import sys
from pathlib import Path

# 将项目根目录加入 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.lang_series_project.benchmark.errors import (
    ErrorType, LLMAPIError, classify_http_error
)
from src.lang_series_project.benchmark.models import (
    TokenUsage, CallResult, ProviderReport, BenchmarkReport
)


# ─────────────────────────────────────────────
#  错误分类测试
# ─────────────────────────────────────────────

class TestErrorClassification:
    """验证错误类型分类器"""

    def test_401_becomes_invalid_key(self):
        error = classify_http_error(401, {"error": {"message": "Unauthorized"}}, "test")
        assert error.error_type == ErrorType.INVALID_KEY
        assert error.status_code == 401

    def test_429_becomes_rate_limit(self):
        error = classify_http_error(429, {"error": {"message": "Too Many Requests"}}, "test")
        assert error.error_type == ErrorType.RATE_LIMIT
        assert error.status_code == 429

    def test_403_becomes_permission_denied(self):
        error = classify_http_error(403, {"error": {"message": "Forbidden"}}, "test")
        assert error.error_type == ErrorType.PERMISSION_DENIED

    def test_500_becomes_server_error(self):
        error = classify_http_error(500, {"error": {"message": "Internal Server Error"}}, "test")
        assert error.error_type == ErrorType.SERVER_ERROR

    def test_503_becomes_server_error(self):
        error = classify_http_error(503, {}, "test")
        assert error.error_type == ErrorType.SERVER_ERROR

    def test_unknown_code(self):
        error = classify_http_error(418, {}, "test")  # I'm a teapot
        assert error.error_type == ErrorType.UNKNOWN

    def test_provider_name_preserved(self):
        error = classify_http_error(401, {}, "deepseek")
        assert error.provider == "deepseek"

    def test_error_to_dict(self):
        error = classify_http_error(429, {"error": {"message": "Rate limited"}}, "openai")
        d = error.to_dict()
        assert d["error_type"] == "rate_limit"
        assert d["status_code"] == 429
        assert d["provider"] == "openai"


# ─────────────────────────────────────────────
#  数据模型测试
# ─────────────────────────────────────────────

class TestTokenUsage:
    def test_default_values(self):
        usage = TokenUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    def test_to_dict(self):
        usage = TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        d = usage.to_dict()
        assert d == {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}


class TestCallResult:
    def test_default_success_false(self):
        result = CallResult(
            provider="test", model="test-model", mode="sync", call_index=0
        )
        assert result.success is False

    def test_to_dict_structure(self):
        result = CallResult(
            provider="deepseek",
            model="deepseek-chat",
            mode="async",
            call_index=1,
            success=True,
            content="机器学习是让机器从数据中学习的技术。",
            latency_ms=1234.56,
        )
        d = result.to_dict()
        assert d["provider"] == "deepseek"
        assert d["success"] is True
        assert d["latency_ms"] == 1234.56
        assert "token_usage" in d


class TestProviderReport:
    def _make_result(self, success: bool, latency: float = 1000.0) -> CallResult:
        r = CallResult(
            provider="test", model="test", mode="sync", call_index=0
        )
        r.success = success
        r.latency_ms = latency
        return r

    def test_finalize_success_rate(self):
        report = ProviderReport(provider="test", model="test")
        report.sync_results = [
            self._make_result(True, 1000),
            self._make_result(False),
        ]
        report.async_results = [
            self._make_result(True, 500),
            self._make_result(True, 600),
        ]
        report.finalize()
        assert report.sync_success_rate == 0.5
        assert report.async_success_rate == 1.0

    def test_finalize_avg_latency(self):
        report = ProviderReport(provider="test", model="test")
        report.sync_results = [self._make_result(True, 2000)]
        report.async_results = [
            self._make_result(True, 500),
            self._make_result(True, 1500),
        ]
        report.finalize()
        assert report.sync_avg_latency_ms == 2000.0
        assert report.async_avg_latency_ms == 1000.0
        # 加速比 = 2000 / 1000 = 2.0
        assert report.speedup_ratio == 2.0

    def test_finalize_no_success(self):
        report = ProviderReport(provider="test", model="test")
        report.sync_results = [self._make_result(False)]
        report.async_results = [self._make_result(False)]
        report.finalize()
        assert report.sync_avg_latency_ms == 0.0
        assert report.speedup_ratio == 0.0


class TestBenchmarkReport:
    def test_to_json_valid(self):
        import json
        report = BenchmarkReport(
            benchmark_id="test-001",
            created_at="2025-01-01T00:00:00Z",
            test_prompt="测试",
            concurrent_requests=3,
        )
        json_str = report.to_json()
        data = json.loads(json_str)
        assert data["benchmark_id"] == "test-001"
        assert data["test_prompt"] == "测试"
        assert data["providers"] == []
