"""
main.py - 系统入口与执行验证
知识点:
  - graph.stream() 逐步事件流追踪（vs invoke() 一次性执行）
  - thread_id 配合 MemorySaver 实现状态持久化和审计
  - 初始 state 的设计（必须包含所有 Annotated 字段的初始值）
  - 时间测量：perf_counter 精度 vs time.time 的区别
  - 日志配置（结构化 logging + Rich Handler）
"""
from __future__ import annotations

import time
import uuid
import logging
import sys

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel

from src.graph import build_graph, print_graph_structure
from src.state import Phase
from src.reporter import render_execution_report

# ── 日志配置 ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)
logger = logging.getLogger(__name__)
console = Console()


def run_research(query: str, show_graph: bool = True) -> dict:
    """
    执行研究报告生成流程。

    参数:
        query: 研究主题（自然语言）
        show_graph: 是否打印 Mermaid 图结构

    返回:
        最终状态字典（包含 final_report 和 contributions）
    """
    console.print(Panel(
        f"[bold white]研究主题：[cyan]{query}[/cyan][/bold white]",
        title="[bold magenta]🚀 多代理研究报告生成系统[/bold magenta]",
        border_style="magenta",
        padding=(1, 4),
    ))

    # ── 构建图 ───────────────────────────────────────────────
    logger.info("正在构建工作流图...")
    graph = build_graph()

    if show_graph:
        print_graph_structure(graph)

    # ── 初始状态（必须包含所有 Reducer 字段的初始空列表）────────
    # 知识点：Annotated[list, operator.add] 的字段必须在 initial_state 中提供初始值
    # 否则 LangGraph 无法正确合并并行节点的返回值
    initial_state = {
        "query": query,
        "phase": Phase.PLAN,
        "subtopics": [],
        "search_results": [],   # Reducer 初始值
        "summaries": [],        # Reducer 初始值
        "final_report": "",
        "contributions": [],    # Reducer 初始值
        "errors": [],           # Reducer 初始值
        "audit_log": [],        # Reducer 初始值
    }

    # ── 每次执行使用唯一 thread_id，便于 MemorySaver 追踪 ─────
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    logger.info(f"执行 ID (thread_id): {thread_id}")

    # ── 执行图（使用 stream 模式，实时查看事件流）─────────────
    # 知识点：graph.stream() vs graph.invoke()
    #   - invoke()：阻塞直到完成，返回最终 state
    #   - stream()：迭代返回每个节点的 (event_type, chunk) 对，可实时监控
    console.print("\n[bold blue]▶ 开始执行工作流...[/bold blue]\n")
    wall_start = time.perf_counter()

    final_state = None
    step_count = 0

    try:
        for event in graph.stream(initial_state, config, stream_mode="updates"):
            step_count += 1
            for node_name, updates in event.items():
                if node_name == "__interrupt__":
                    continue
                fields = list(updates.keys()) if isinstance(updates, dict) else []
                console.print(
                    f"  [dim]Step {step_count:02d}[/dim] "
                    f"[bold green]{node_name}[/bold green] "
                    f"[dim]→ 更新字段: {fields}[/dim]"
                )

        # 获取最终状态
        final_state = graph.get_state(config).values

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ 用户中断执行[/yellow]")
        sys.exit(0)
    except Exception as exc:
        console.print(f"\n[red]❌ 执行失败: {exc}[/red]")
        logger.exception("图执行异常")
        raise

    wall_end = time.perf_counter()
    total_wall_time = wall_end - wall_start

    logger.info(f"工作流执行完成，总耗时: {total_wall_time:.3f}s，共 {step_count} 个步骤")

    # ── 渲染执行报告 ─────────────────────────────────────────
    render_execution_report(final_state, total_wall_time)

    return final_state


def main():
    """命令行入口。"""
    import argparse

    parser = argparse.ArgumentParser(
        description="多代理研究报告生成系统 - 基于 LangGraph + DeepSeek"
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        default="AI Agent在2025年的技术进展与商业化应用",
        help="研究主题（默认：AI Agent在2025年的技术进展与商业化应用）",
    )
    parser.add_argument(
        "--no-graph",
        action="store_true",
        help="不打印 Mermaid 图结构",
    )
    args = parser.parse_args()

    run_research(query=args.query, show_graph=not args.no_graph)


if __name__ == "__main__":
    main()
