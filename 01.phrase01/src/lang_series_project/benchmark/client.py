"""
DeepSeek API 客户端模块 - 采用现代 TaskGroup 并发模型
"""
import asyncio
import time
from datetime import datetime, timezone

import httpx

from .config import DeepSeekConfig
from .errors import LLMAPIError, ErrorType, classify_http_error
from .models import CallResult, TokenUsage


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_payload(model: str, prompt: str) -> dict:
    return {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 256,
        "temperature": 0.7,
        "stream": False
    }


def _parse_response(data: dict) -> tuple[str, TokenUsage]:
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    token_usage = TokenUsage(
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
    )
    return content, token_usage


def _build_headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _api_url(base_url: str) -> str:
    return f"{base_url}/chat/completions"


# ─────────────────────────────────────────────
#  同步客户端
# ─────────────────────────────────────────────

def call_sync(config: DeepSeekConfig, prompt: str, call_index: int = 0) -> CallResult:
    """同步调用"""
    result = CallResult(provider="DeepSeek", model=config.model, mode="sync", call_index=call_index)
    result.start_time = _now_iso()
    t0 = time.perf_counter()

    try:
        with httpx.Client(timeout=config.timeout) as client:
            response = client.post(
                url=_api_url(config.base_url),
                headers=_build_headers(config.api_key),
                json=_build_payload(config.model, prompt),
            )
        result.latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        result.end_time = _now_iso()
        result.status_code = response.status_code

        body = response.json()
        if response.status_code != 200:
            error = classify_http_error(response.status_code, body, "DeepSeek")
            result.error_type = error.error_type.value
            result.error_message = error.message
            return result

        content, usage = _parse_response(body)
        result.success = True
        result.content = content
        result.token_usage = usage

    except Exception as e:
        result.latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        result.end_time = _now_iso()
        result.error_type = ErrorType.UNKNOWN.value
        result.error_message = f"错误: {str(e)}"
    return result


# ─────────────────────────────────────────────
#  异步客户端 (Modern TaskGroup!)
# ─────────────────────────────────────────────

async def call_async(
    config: DeepSeekConfig,
    prompt: str,
    call_index: int = 0,
    client: httpx.AsyncClient | None = None,
) -> CallResult:
    """单个异步调用请求块"""
    result = CallResult(provider="DeepSeek", model=config.model, mode="async", call_index=call_index)
    result.start_time = _now_iso()
    t0 = time.perf_counter()

    _own_client = client is None
    if _own_client:
        client = httpx.AsyncClient(timeout=config.timeout)

    try:
        response = await client.post(
            url=_api_url(config.base_url),
            headers=_build_headers(config.api_key),
            json=_build_payload(config.model, prompt),
        )
        result.latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        result.end_time = _now_iso()
        result.status_code = response.status_code

        body = response.json()
        if response.status_code != 200:
            error = classify_http_error(response.status_code, body, "DeepSeek")
            result.error_type = error.error_type.value
            result.error_message = error.message
            return result

        content, usage = _parse_response(body)
        result.success = True
        result.content = content
        result.token_usage = usage

    except Exception as e:
        result.latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        result.end_time = _now_iso()
        result.error_type = ErrorType.UNKNOWN.value
        result.error_message = str(e)
    finally:
        if _own_client:
            await client.aclose()
    return result


async def call_async_concurrent(
    config: DeepSeekConfig,
    prompt: str,
    n: int = 3,
) -> list[CallResult]:
    """
    【升级：使用 TaskGroup 实现】
    现代的结构化并发方式
    """
    async with httpx.AsyncClient(timeout=config.timeout) as client:
        # 1. 使用 TaskGroup 开启作用域
        async with asyncio.TaskGroup() as tg:
            # 2. 批量创建任务并放入作用域内管理
            tasks = [
                tg.create_task(call_async(config, prompt, i, client)) 
                for i in range(n)
            ]
        
        # 3. 当代码运行到这里时，TaskGroup 会确保内部所有任务都已执行完毕
        # 如果有任何一个任务异常崩溃，这里会自动捕获并清理
        results = [t.result() for t in tasks]
        
    return list(results)
