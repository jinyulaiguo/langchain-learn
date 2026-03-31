"""
supervisor.py - Supervisor 代理（调度中枢）
知识点:
  - Supervisor 不直接处理内容，只负责：任务分解、路由决策、Send API 调度
  - 返回 Send 对象列表实现并行 Worker 触发
  - 条件边（Conditional Edge）函数依赖 Phase 枚举做路由
  - 审计日志（audit_log）记录每次调度决策
  - 工作流阶段: plan → search(并行) → summarize(并行) → format → done
"""
from __future__ import annotations

import logging
import time
from typing import Any, Sequence, Union

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langgraph.types import Send

from .config import get_llm, PARALLEL_WORKERS
from .state import (
    ReportState,
    SearchInput,
    SummarizeInput,
    Phase,
)

logger = logging.getLogger(__name__)

# ── 任务规划 Prompt ──────────────────────────────────────────
_PLAN_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "你是一位研究项目规划专家。给定一个研究主题，将其拆解为 {num_subtopics} 个独立的子研究方向。\n"
     "输出 JSON 格式（只输出 JSON，不要有其他文字）：\n"
     '{{"subtopics": ["子主题1", "子主题2", "子主题3"]}}\n'
     "要求：子主题之间应该互补而不重叠，涵盖该研究主题的不同维度。"),
    ("human", "研究主题：{query}"),
])


def supervisor_plan_node(state: ReportState) -> dict[str, Any]:
    """
    阶段1：任务规划。
    Supervisor 接收用户 query，利用 LLM 拆解为若干子主题，写入 state。
    """
    query = state["query"]
    start = time.perf_counter()

    logger.info(f"[Supervisor] 开始任务规划: {query!r}")

    llm = get_llm(temperature=0.1)
    parser = JsonOutputParser()
    chain = _PLAN_PROMPT | llm | parser

    try:
        result = chain.invoke({"query": query, "num_subtopics": PARALLEL_WORKERS})
        subtopics: list[str] = result.get("subtopics", [])
        if not subtopics:
            raise ValueError("LLM 返回的 subtopics 列表为空")
    except Exception as exc:
        logger.warning(f"[Supervisor] 规划解析失败，使用默认子主题: {exc}")
        # 后备方案：生成默认子主题
        subtopics = [
            f"{query} - 技术发展现状",
            f"{query} - 经济与社会影响",
            f"{query} - 未来趋势预测",
        ]

    elapsed = round(time.perf_counter() - start, 3)
    audit_msg = (
        f"[Supervisor-Plan] 耗时 {elapsed}s | "
        f"研究主题: {query!r} | "
        f"拆解子主题: {subtopics}"
    )
    logger.info(audit_msg)

    return {
        "subtopics": subtopics,
        "phase": Phase.SEARCH,
        "audit_log": [audit_msg],
    }


# ── 路由：调度 Search Workers（并行）──────────────────────────

def supervisor_dispatch_search(state: ReportState) -> list[Send]:
    """
    条件边函数，或直接作为 Node 使用。
    返回 Send 对象列表 → LangGraph 会并行执行所有 Search Worker。

    知识点：Send(node_name, state_dict) 让 LangGraph 同时启动多个节点实例，
    每个实例都有自己独立的输入，结果通过 Reducer 合并回全局 state。
    """
    subtopics: list[str] = state.get("subtopics", [])
    query: str = state["query"]

    sends = []
    for i, subtopic in enumerate(subtopics):
        search_input = SearchInput(
            task_id=str(i),
            subtopic=subtopic,
            query=query,
            retry_count=0,
        )
        sends.append(Send("search_worker", search_input))

    audit_msg = f"[Supervisor-Dispatch-Search] 并行调度 {len(sends)} 个 Search Worker"
    logger.info(audit_msg)

    return sends


def supervisor_search_dispatch_node(state: ReportState) -> dict[str, Any]:
    """包装为 Node，记录审计日志后触发 Send。"""
    audit_msg = f"[Supervisor] 进入搜索调度阶段，共 {len(state.get('subtopics', []))} 个子主题"
    logger.info(audit_msg)
    return {
        "phase": Phase.SUMMARIZE,
        "audit_log": [audit_msg],
    }


# ── 路由：调度 Summarize Workers（并行）─────────────────────

def supervisor_dispatch_summarize(state: ReportState) -> list[Send]:
    """
    Search 阶段结束后，对每个搜索结果并行触发 Summarize Worker。
    """
    search_results: list[dict] = state.get("search_results", [])
    query: str = state["query"]

    sends = []
    for item in search_results:
        summ_input = SummarizeInput(
            task_id=item["task_id"],
            source_text=item["content"],
            subtopic=item["subtopic"],
            query=query,
            retry_count=0,
        )
        sends.append(Send("summarize_worker", summ_input))

    audit_msg = f"[Supervisor-Dispatch-Summarize] 并行调度 {len(sends)} 个 Summarize Worker"
    logger.info(audit_msg)
    return sends


def supervisor_summarize_dispatch_node(state: ReportState) -> dict[str, Any]:
    """包装为 Node，记录审计日志后触发 Send。"""
    audit_msg = (
        f"[Supervisor] 进入摘要调度阶段，"
        f"待摘要数量: {len(state.get('search_results', []))}"
    )
    logger.info(audit_msg)
    return {
        "phase": Phase.FORMAT,
        "audit_log": [audit_msg],
    }


# ── 路由决策函数（Conditional Edge）────────────────────────────

def route_by_phase(state: ReportState) -> str:
    """
    供 add_conditional_edges 使用的路由函数。
    根据 state["phase"] 返回下一个节点名称。

    知识点：返回值必须与 graph.add_conditional_edges 的第三个参数（映射字典）中的 key 对应。
    """
    phase = state.get("phase", Phase.PLAN)
    route_map = {
        Phase.PLAN: "supervisor_plan",
        Phase.SEARCH: "supervisor_search_dispatch",
        Phase.SUMMARIZE: "supervisor_summarize_dispatch",
        Phase.FORMAT: "format_worker",
        Phase.DONE: "__end__",
    }
    next_node = route_map.get(phase, "__end__")
    logger.debug(f"[Router] phase={phase} → {next_node}")
    return next_node
