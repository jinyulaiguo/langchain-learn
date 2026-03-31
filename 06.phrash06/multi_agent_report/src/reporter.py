"""
reporter.py - 执行结果报告渲染
知识点:
  - Rich 库用于美化终端输出（表格、面板、颜色）
  - 分析 WorkerContribution 列表，计算并发加速比
  - 生成人类可读的执行时间对比数据
"""
from __future__ import annotations

import time
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from .state import WorkerContribution, ReportState

console = Console()


def render_execution_report(state: dict, total_wall_time: float) -> None:
    """渲染完整的执行报告，包括并发时间分析和 Worker 贡献表格。"""

    contributions: list[WorkerContribution] = state.get("contributions", [])
    audit_log: list[str] = state.get("audit_log", [])
    errors: list[str] = [e for e in state.get("errors", []) if e]
    final_report: str = state.get("final_report", "")

    # ── 1. 打印最终报告 ────────────────────────────────────
    console.print("\n")
    console.print(Panel(
        Text(final_report, style="white"),
        title="[bold cyan]📄 最终研究报告[/bold cyan]",
        border_style="cyan",
        padding=(1, 2),
    ))

    # ── 2. Worker 执行时间表格 ─────────────────────────────
    table = Table(
        title="⚙️ Worker 执行统计",
        box=box.ROUNDED,
        header_style="bold magenta",
        show_lines=True,
    )
    table.add_column("Worker ID", style="cyan", no_wrap=True)
    table.add_column("类型", style="white")
    table.add_column("子任务", style="white", max_width=40)
    table.add_column("耗时 (s)", style="yellow", justify="right")
    table.add_column("重试次数", justify="center")
    table.add_column("状态", justify="center")
    table.add_column("贡献摘要", style="dim", max_width=50)

    search_workers = [c for c in contributions if c["worker_type"] == "search"]
    summarize_workers = [c for c in contributions if c["worker_type"] == "summarize"]
    format_workers = [c for c in contributions if c["worker_type"] == "format"]

    for group in [search_workers, summarize_workers, format_workers]:
        for c in sorted(group, key=lambda x: x["start_time"]):
            status_icon = {
                "success": "[green]✅ 成功[/green]",
                "failed_recovered": "[yellow]⚠️ 降级[/yellow]",
                "failed": "[red]❌ 失败[/red]",
            }.get(c["status"], c["status"])

            table.add_row(
                c["worker_id"],
                c["worker_type"],
                c["subtask"],
                f"{c['duration']:.3f}",
                str(c["retry_count"]),
                status_icon,
                c["output_summary"][:80] + "..." if len(c["output_summary"]) > 80 else c["output_summary"],
            )

    console.print(table)

    # ── 3. 并发加速比分析 ──────────────────────────────────
    _print_parallelism_analysis(search_workers, summarize_workers, total_wall_time)

    # ── 4. Supervisor 审计日志 ────────────────────────────
    if audit_log:
        console.print(Panel(
            "\n".join(f"  • {log}" for log in audit_log),
            title="[bold blue]🗂️ Supervisor 审计日志[/bold blue]",
            border_style="blue",
            padding=(0, 2),
        ))

    # ── 5. 错误报告 ───────────────────────────────────────
    if errors:
        console.print(Panel(
            "\n".join(f"  ⚠️ {e}" for e in errors),
            title="[bold red]🚨 错误记录[/bold red]",
            border_style="red",
            padding=(0, 2),
        ))
    else:
        console.print("[green]✅ 全部 Worker 执行成功，无错误记录。[/green]\n")


def _print_parallelism_analysis(
    search_workers: list[WorkerContribution],
    summarize_workers: list[WorkerContribution],
    total_wall_time: float,
) -> None:
    """计算并行加速比并打印对比数据。"""

    def analyze_group(workers: list[WorkerContribution], label: str) -> None:
        if not workers:
            return
        sequential_time = sum(w["duration"] for w in workers)
        if len(workers) > 1:
            # 并行实际耗时 = max(end_time) - min(start_time)
            actual_parallel_time = (
                max(w["end_time"] for w in workers) -
                min(w["start_time"] for w in workers)
            )
            speedup = sequential_time / actual_parallel_time if actual_parallel_time > 0 else 1.0
        else:
            actual_parallel_time = workers[0]["duration"]
            speedup = 1.0

        console.print(f"\n[bold]{label} 阶段并发分析:[/bold]")
        console.print(f"  Workers 数量:        {len(workers)}")
        console.print(f"  串行假设总耗时:       [red]{sequential_time:.3f}s[/red]")
        console.print(f"  并行实际耗时:         [green]{actual_parallel_time:.3f}s[/green]")
        console.print(f"  加速比 (Speedup):     [bold yellow]{speedup:.2f}×[/bold yellow]")
        for w in workers:
            bar_len = max(1, int(w["duration"] * 20 / (sequential_time / len(workers) + 0.001)))
            bar = "█" * min(bar_len, 40)
            console.print(f"    [{w['worker_id']}] {bar} {w['duration']:.3f}s")

    console.print(Panel(
        "",
        title="[bold green]⚡ 并发执行分析报告[/bold green]",
        border_style="green",
    ))

    analyze_group(search_workers, "🔍 Search")
    analyze_group(summarize_workers, "📝 Summarize")
    console.print(f"\n  [bold]整体 Wall Time: [cyan]{total_wall_time:.3f}s[/cyan][/bold]\n")
