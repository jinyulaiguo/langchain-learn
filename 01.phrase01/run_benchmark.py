"""
LLM API 调用基准测试器 - 主入口

用法:
    uv run python run_benchmark.py                    # 运行完整基准测试
    uv run python run_benchmark.py --error-tests      # 同时验证错误覆盖率
    uv run python run_benchmark.py --prompt "你的问题"  # 自定义 prompt
    uv run python run_benchmark.py --concurrent 5     # 修改并发数
"""
import argparse
import json
import sys
from pathlib import Path

# 底层逻辑导入
from src.lang_series_project.benchmark.config import load_config
from src.lang_series_project.benchmark.runner import run_benchmark, save_report

def parse_args() -> argparse.Namespace:
    """回复原始 argparse 逻辑，不改动任何功能项"""
    parser = argparse.ArgumentParser(
        description="LLM API 调用基准测试器 — 直接调用 REST API，无 SDK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  uv run python run_benchmark.py
  uv run python run_benchmark.py --error-tests
  uv run python run_benchmark.py --prompt "什么是深度学习？" --concurrent 5
        """
    )
    parser.add_argument(
        "--prompt", "-p",
        default="请用一句话解释什么是机器学习。",
        help="发送给 LLM 的测试 prompt（默认：机器学习解释）"
    )
    parser.add_argument(
        "--concurrent", "-c",
        type=int,
        default=3,
        help="异步并发请求数量（默认：3）"
    )
    parser.add_argument(
        "--error-tests", "-e",
        action="store_true",
        help="同时运行错误处理覆盖率验证"
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="benchmark_results",
        help="JSON 报告输出目录（默认：benchmark_results）"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="不保存 JSON 报告文件"
    )
    return parser.parse_args()


def main() -> int:
    """主函数，返回退出码"""
    args = parse_args()

    # ── 1. 加载配置 ──────────────────────────────────
    try:
        config = load_config()
        config.test_prompt = args.prompt
        config.concurrent_requests = args.concurrent
        config.output_dir = Path(args.output_dir)
    except EnvironmentError as e:
        print(f"\n❌ 配置错误:\n{e}\n", file=sys.stderr)
        return 1

    # ── 2. 运行错误覆盖率测试（如果用户指定了 --error-tests） ──
    error_coverage = None
    if args.error_tests:
        from src.lang_series_project.benchmark.error_tests import run_error_coverage_tests
        # 使用 DeepSeek 配置进行故障注入测试
        error_coverage = run_error_coverage_tests(config.api)

    # ── 3. 运行基准测试 ──────────────────────────────
    report = run_benchmark(config)

    # 注入错误测试结果
    if error_coverage is not None:
        print("\n📋 错误覆盖率测试结果:")
        print(json.dumps(error_coverage, ensure_ascii=False, indent=2))

    # ── 4. 保存 JSON 报告 ────────────────────────────
    if not args.no_save:
        saved_path = save_report(report, config.output_dir)
        
        # 如果有错误覆盖率测试，追加到文件
        if error_coverage is not None:
            with open(saved_path, "r", encoding="utf-8") as f:
                full_report = json.load(f)
            full_report["error_coverage_test"] = error_coverage
            with open(saved_path, "w", encoding="utf-8") as f:
                json.dump(full_report, f, ensure_ascii=False, indent=2)

    # ── 5. 打印最终 JSON 报告预览 ────────────────────
    print("\n📊 完整 JSON 报告预览:")
    print(report.to_json())

    return 0


if __name__ == "__main__":
    sys.exit(main())
