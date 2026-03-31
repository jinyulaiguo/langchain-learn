"""
graph.py - LangGraph 工作流图构建
知识点:
  - StateGraph 构建、节点注册、边定义
  - add_conditional_edges + Send API 实现动态并行分支
  - 使用 Send 函数作为边，触发并行 Worker 实例
  - MemorySaver 持久化（便于断点续传和审计）
  - graph.compile() 与 graph.get_graph().draw_mermaid() 可视化
  - CompiledGraph 的类型标注
"""
from __future__ import annotations

import logging
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .state import ReportState, Phase
from .workers import search_worker_node, summarize_worker_node, format_worker_node
from .supervisor import (
    supervisor_plan_node,
    supervisor_search_dispatch_node,
    supervisor_summarize_dispatch_node,
    supervisor_dispatch_search,
    supervisor_dispatch_summarize,
    route_by_phase,
)

logger = logging.getLogger(__name__)


def build_graph():
    """
    构建多代理研究报告生成工作流图。

    图结构（节点流向）:
    ┌─────────────────────────────────────────────────┐
    │  START                                          │
    │    ↓                                            │
    │  supervisor_plan  ← Supervisor 任务规划          │
    │    ↓ (phase=SEARCH)                             │
    │  supervisor_search_dispatch ← 调度并发搜索        │
    │    ↓ (Send API → N个并行实例)                    │
    │  search_worker × N  (并行)                       │
    │    ↓ (全部完成后 Reducer 合并)                   │
    │  supervisor_summarize_dispatch ← 调度并发摘要      │
    │    ↓ (Send API → N个并行实例)                    │
    │  summarize_worker × N  (并行)                    │
    │    ↓ (全部完成后 Reducer 合并)                   │
    │  format_worker  ← 串行格式化报告                  │
    │    ↓ (phase=DONE)                               │
    │  END                                            │
    └─────────────────────────────────────────────────┘

    关键设计:
    - Workers 之间不直接通信，全部通过 Supervisor 节点调度
    - Search Worker 和 Summarize Worker 各自通过 Send API 并行执行
    - Format Worker 串行执行，依赖所有 Summarize 结果
    - MemorySaver 支持状态持久化，可通过 thread_id 审计每次执行
    """
    graph = StateGraph(ReportState)

    # ── 注册节点 ────────────────────────────────────────────
    graph.add_node("supervisor_plan", supervisor_plan_node)
    graph.add_node("supervisor_search_dispatch", supervisor_search_dispatch_node)
    graph.add_node("supervisor_summarize_dispatch", supervisor_summarize_dispatch_node)
    graph.add_node("search_worker", search_worker_node)
    graph.add_node("summarize_worker", summarize_worker_node)
    graph.add_node("format_worker", format_worker_node)

    # ── 定义边 ──────────────────────────────────────────────

    # 1. 入口：START → supervisor_plan
    graph.add_edge(START, "supervisor_plan")

    # 2. 规划完成 → 搜索调度节点
    graph.add_edge("supervisor_plan", "supervisor_search_dispatch")

    # 3. 搜索调度节点 → 并行 Search Workers
    #    add_conditional_edges 的第二个参数是一个函数，返回 Send 列表表示并行执行
    #    知识点: 当路由函数返回 list[Send] 时，LangGraph 自动并行调度所有 Worker
    graph.add_conditional_edges(
        "supervisor_search_dispatch",
        supervisor_dispatch_search,  # 返回 list[Send("search_worker", input)]
    )

    # 4. 所有 Search Workers 完成 → 摘要调度节点
    graph.add_edge("search_worker", "supervisor_summarize_dispatch")

    # 5. 摘要调度节点 → 并行 Summarize Workers
    graph.add_conditional_edges(
        "supervisor_summarize_dispatch",
        supervisor_dispatch_summarize,  # 返回 list[Send("summarize_worker", input)]
    )

    # 6. 所有 Summarize Workers 完成 → Format Worker（串行）
    graph.add_edge("summarize_worker", "format_worker")

    # 7. Format Worker 完成 → END
    graph.add_edge("format_worker", END)

    # ── 编译（启用 MemorySaver 持久化）──────────────────────
    memory = MemorySaver()
    compiled = graph.compile(checkpointer=memory)

    logger.info("[Graph] 工作流图编译完成")
    return compiled


def print_graph_structure(compiled_graph) -> None:
    """打印 Mermaid 图结构（用于文档和调试）。"""
    try:
        mermaid_str = compiled_graph.get_graph().draw_mermaid()
        print("\n─── Mermaid 图结构 ────────────────────────")
        print(mermaid_str)
        print("───────────────────────────────────────────\n")
    except Exception as e:
        logger.warning(f"无法生成 Mermaid 图: {e}")
