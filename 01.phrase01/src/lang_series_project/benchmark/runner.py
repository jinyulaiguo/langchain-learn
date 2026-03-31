"""
基准测试运行器 - DeepSeek 专版 (修复 APIConfig 引用)
"""
import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .client import call_sync, call_async_concurrent
from .config import BenchmarkConfig, DeepSeekConfig
from .models import BenchmarkReport, ProviderReport, CallResult


def _run_sync_benchmark(config: DeepSeekConfig, prompt: str) -> list[CallResult]:
    """同步测试请求逻辑"""
    print(f"  → [同步] 发起请求 ...")
    result = call_sync(config, prompt, call_index=0)
    if result.success:
        print(f"     ✓ 成功 | 延迟: {result.latency_ms:.0f}ms | Tokens: {result.token_usage.total_tokens}")
    else:
        print(f"     ✗ 失败 | {result.error_type}: {result.error_message}")
    return [result]


def _run_async_benchmark(config: DeepSeekConfig, prompt: str, concurrent: int) -> list[CallResult]:
    """异步测试请求逻辑"""
    print(f"  → [异步] 并发 {concurrent} 个请求 ...")
    results = asyncio.run(call_async_concurrent(config, prompt, n=concurrent))
    success_count = sum(1 for r in results if r.success)
    avg_latency = (
        sum(r.latency_ms for r in results if r.success) / success_count
        if success_count > 0 else 0
    )
    print(f"     ✓ {success_count}/{concurrent} 成功 | 平均延迟: {avg_latency:.0f}ms")
    return list(results)


def run_benchmark(bench_config: BenchmarkConfig) -> BenchmarkReport:
    """运行完整基准测试"""
    benchmark_id = str(uuid.uuid4())[:8]
    created_at = datetime.now(timezone.utc).isoformat()

    print("\n" + "=" * 60)
    print(f"  DeepSeek API 基准测试器 [ID: {benchmark_id}]")
    print("=" * 60)
    print(f"  Prompt  : {bench_config.test_prompt}")
    print(f"  并发数   : {bench_config.concurrent_requests}")
    print("=" * 60)

    # 处理 DeepSeek 报告
    report = ProviderReport(provider="DeepSeek", model=bench_config.api.model)
    report.sync_results = _run_sync_benchmark(bench_config.api, bench_config.test_prompt)
    report.async_results = _run_async_benchmark(bench_config.api, bench_config.test_prompt, bench_config.concurrent_requests)
    report.finalize()

    print(f"\n  📊 对比摘要:")
    print(f"     同步平均延迟  : {report.sync_avg_latency_ms:.0f} ms")
    print(f"     异步平均延迟  : {report.async_avg_latency_ms:.0f} ms")
    if report.speedup_ratio > 0:
        print(f"     加速比        : {report.speedup_ratio:.2f}x")

    benchmark_report = BenchmarkReport(
        benchmark_id=benchmark_id,
        created_at=created_at,
        test_prompt=bench_config.test_prompt,
        concurrent_requests=bench_config.concurrent_requests,
        provider_reports=[report],
    )
    return benchmark_report


def save_report(report: BenchmarkReport, output_dir: Path) -> Path:
    """保存基准测试结果到本地 JSON 文件"""
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"benchmark_{report.benchmark_id}_{report.created_at[:10]}.json"
    output_path = output_dir / filename
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report.to_json())
    print(f"\n  💾 报告已保存: {output_path}")
    return output_path
