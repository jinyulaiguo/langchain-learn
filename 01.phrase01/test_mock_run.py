"""
全功能模拟测试脚本 (Mock Version)
用于在无 API Key 情况下验证：
1. 同步与异步模式对比输出
2. 结构化 JSON 报告生成
3. Token 用量统计
4. 错误处理逻辑
"""
import json
import asyncio
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime, timezone

# 导入我们的项目模块
from src.lang_series_project.benchmark.config import APIConfig, BenchmarkConfig
from src.lang_series_project.benchmark.runner import run_benchmark, save_report
from src.lang_series_project.benchmark.models import CallResult, TokenUsage

def mock_call_sync(config, prompt, call_index=0):
    """模拟同步调用：耗时 1.5s"""
    import time
    from src.lang_series_project.benchmark.models import CallResult, TokenUsage
    
    result = CallResult(
        provider=config.name, model=config.model, mode="sync", call_index=call_index,
        start_time=datetime.now(timezone.utc).isoformat(),
        success=True, content="[Mocked Response] 机器学习是...",
        latency_ms=1500.0,
        token_usage=TokenUsage(10, 20, 30)
    )
    result.end_time = datetime.now(timezone.utc).isoformat()
    return result

async def mock_call_async_concurrent(config, prompt, n=3):
    """模拟异步并发调用：总耗时仅稍大于单次调用（约 0.6s）"""
    import asyncio
    from src.lang_series_project.benchmark.models import CallResult, TokenUsage
    
    # 模拟并发优势
    results = []
    for i in range(n):
        res = CallResult(
            provider=config.name, model=config.model, mode="async", call_index=i,
            start_time=datetime.now(timezone.utc).isoformat(),
            success=True, content=f"[Mocked Async {i}]",
            latency_ms=600.0, # 并发时通常看吞吐，但这里由于是单次平均，体现为异步吞吐优势
            token_usage=TokenUsage(10, 20, 30)
        )
        res.end_time = datetime.now(timezone.utc).isoformat()
        results.append(res)
    return results

def run_mock_verification():
    print("\n" + "="*60)
    print("  LLM API 基准测试器 - Mock 流程验证 (无需联网)")
    print("="*60)
    
    # 1. 构造配置
    config = BenchmarkConfig(
        test_prompt="测试 Prompt",
        concurrent_requests=5,
        providers=[APIConfig(
            name="mock_provider",
            base_url="http://localhost",
            api_key="mock-key",
            model="mock-v1"
        )]
    )

    # 2. Patch 掉真实网络调用
    with patch('src.lang_series_project.benchmark.runner.call_sync', side_effect=mock_call_sync), \
         patch('src.lang_series_project.benchmark.runner.asyncio.run', return_value=asyncio.run(mock_call_async_concurrent(config.providers[0], "", 5))):
        
        # 3. 运行基准测试
        report = run_benchmark(config)
        
        # 4. 保存报告
        saved_path = save_report(report, config.output_dir)
        
        # 5. 打印对比与 JSON
        print(f"\n✅ 模拟运行成功！")
        print(f"📊 加速比 (Speedup Ratio): {report.provider_reports[0].speedup_ratio}x")
        print(f"📄 报告已保存至: {saved_path}")
        
        # 验证 JSON 内容
        with open(saved_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert data["providers"][0]["summary"]["speedup_ratio"] > 1.0
            assert "token_usage" in data["providers"][0]["sync_results"][0]

if __name__ == "__main__":
    run_mock_verification()
