"""
错误处理验证模块 - DeepSeek 专版
"""
import asyncio
from .client import call_sync
from .config import DeepSeekConfig # 修正引用
from .errors import ErrorType
from .models import CallResult


def test_timeout_error(real_config: DeepSeekConfig) -> CallResult:
    """验证超时捕捉"""
    print("\n  [错误测试] 1/3 超时错误")
    # 构造低延迟配置强制触发超时
    timeout_config = DeepSeekConfig(
        api_key=real_config.api_key,
        base_url=real_config.base_url,
        model=real_config.model,
        timeout=0.001,
    )
    result = call_sync(timeout_config, "ping", call_index=0)
    _assert_error_type(result, ErrorType.TIMEOUT, "超时错误")
    return result


def test_invalid_key_error(real_config: DeepSeekConfig) -> CallResult:
    """验证无效密钥捕捉"""
    print("\n  [错误测试] 2/3 无效密钥 (401)")
    bad_key_config = DeepSeekConfig(
        api_key="sk-INVALID_KEY_12345",
        base_url=real_config.base_url,
        model=real_config.model,
    )
    result = call_sync(bad_key_config, "ping", call_index=0)
    _assert_error_type(result, ErrorType.INVALID_KEY, "无效密钥")
    return result


def test_rate_limit_simulation(real_config: DeepSeekConfig) -> CallResult:
    """模拟速率限制 (429) 分类"""
    print("\n  [错误测试] 3/3 Rate Limit 分类验证")
    from .errors import classify_http_error
    result = CallResult(provider="DeepSeek", model="mock", mode="sync", call_index=0)
    error = classify_http_error(429, {"error": {"message": "Too Many Requests"}}, "DeepSeek")
    assert error.error_type == ErrorType.RATE_LIMIT
    result.error_type = error.error_type.value
    result.error_message = error.message
    print(f"     ✓ 分类器正确识别 Rate Limit: {error.message}")
    return result


def _assert_error_type(result: CallResult, expected: ErrorType, label: str):
    assert not result.success, f"{label} 应当失败"
    assert result.error_type == expected.value
    print(f"     ✓ 正确捕获 [{result.error_type}]")


def run_error_coverage_tests(real_config: DeepSeekConfig) -> dict:
    """运行错误验证流程"""
    print("\n" + "─" * 50)
    print("  ⚡ 错误处理覆盖率验证 (DeepSeek)")
    print("─" * 50)
    
    passed = 0
    results = {}
    for name, fn in [("timeout", test_timeout_error), 
                     ("invalid_key", test_invalid_key_error), 
                     ("rate_limit", test_rate_limit_simulation)]:
        try:
            res = fn(real_config)
            results[name] = {"status": "PASS", "type": res.error_type}
            passed += 1
        except Exception as e:
            results[name] = {"status": "FAIL", "reason": str(e)}
            
    return {"passed_count": passed, "total": 3, "details": results}
