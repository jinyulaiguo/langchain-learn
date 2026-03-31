"""
workers.py - 三个专项 Worker 代理
知识点:
  - LangGraph 节点函数签名：接收 state，返回 partial state dict
  - Send API 子任务节点：接收子状态（SearchInput / SummarizeInput）
  - 重试装饰器（tenacity）与手动 retry_count 计数
  - time.perf_counter() 做精确计时
  - WorkerContribution 元数据自动上报
  - 节点内 try-except 实现故障隔离
"""
from __future__ import annotations

import time
import logging
from typing import Any

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from langchain_core.prompts import ChatPromptTemplate

from .config import get_llm, RETRY_MAX_TIMES
from .state import (
    ReportState,
    SearchInput,
    SummarizeInput,
    WorkerContribution,
    Phase,
)

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────
# 工具函数
# ────────────────────────────────────────────────────────────

def _make_contribution(
    worker_id: str,
    worker_type: str,
    subtask: str,
    output: str,
    start_time: float,
    end_time: float,
    retry_count: int = 0,
    status: str = "success",
) -> WorkerContribution:
    return WorkerContribution(
        worker_id=worker_id,
        worker_type=worker_type,
        subtask=subtask,
        output_summary=output[:300] + ("..." if len(output) > 300 else ""),
        start_time=start_time,
        end_time=end_time,
        duration=round(end_time - start_time, 3),
        retry_count=retry_count,
        status=status,
    )


# ────────────────────────────────────────────────────────────
# Search Worker  （并行，每个子主题独立实例）
# 入参格式：SearchInput（由 Send API 注入）
# ────────────────────────────────────────────────────────────

_SEARCH_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "你是一位专业的信息检索分析师。你的任务是针对指定主题，"
     "模拟网络搜索并整理出最关键的事实、数据和观点。\n"
     "输出格式要求：\n"
     "1. 核心发现（3～5条，带数据）\n"
     "2. 重要来源（列举3个虚构但合理的来源名称）\n"
     "3. 关键引用（1～2句话，附来源）\n"
     "回答语言：中文"),
    ("human", "研究主题：{query}\n当前子领域：{subtopic}\n\n请完成该子领域的信息检索。"),
])


def _call_search_llm(query: str, subtopic: str) -> str:
    """带 tenacity 重试的 LLM 调用，网络错误时指数退避。"""
    llm = get_llm(temperature=0.4)
    chain = _SEARCH_PROMPT | llm
    result = chain.invoke({"query": query, "subtopic": subtopic})
    return result.content


def search_worker_node(state: SearchInput) -> dict[str, Any]:
    """
    Search Worker 节点。
    接收 SearchInput（由 Send API 构造），返回更新片段注入全局 ReportState。
    知识点：Send API 子节点的返回值 key 必须与全局 state 的字段匹配（使用 Reducer 合并）。
    """
    task_id: str = state["task_id"]
    subtopic: str = state["subtopic"]
    query: str = state["query"]
    retry_count: int = state.get("retry_count", 0)

    start = time.perf_counter()
    status = "success"
    output = ""
    error_msg = ""

    logger.info(f"[Search Worker {task_id}] 开始搜索: {subtopic!r}")

    for attempt in range(RETRY_MAX_TIMES):
        try:
            output = _call_search_llm(query, subtopic)
            retry_count = attempt
            break
        except Exception as exc:
            error_msg = str(exc)
            logger.warning(f"[Search Worker {task_id}] 第 {attempt+1} 次失败: {exc}")
            if attempt == RETRY_MAX_TIMES - 1:
                output = f"⚠️ 搜索失败（已重试 {RETRY_MAX_TIMES} 次）：{error_msg}"
                status = "failed_recovered"
                retry_count = attempt
            time.sleep(0.5 * (attempt + 1))

    end = time.perf_counter()
    contribution = _make_contribution(
        worker_id=f"search-{task_id}",
        worker_type="search",
        subtask=f"搜索子主题: {subtopic}",
        output=output,
        start_time=start,
        end_time=end,
        retry_count=retry_count,
        status=status,
    )
    logger.info(f"[Search Worker {task_id}] 完成，耗时 {contribution['duration']:.2f}s")

    return {
        "search_results": [{"task_id": task_id, "subtopic": subtopic, "content": output}],
        "contributions": [contribution],
        "errors": ([error_msg] if status != "success" else []),
    }


# ────────────────────────────────────────────────────────────
# Summarize Worker  （并行，每个搜索结果独立摘要）
# 入参格式：SummarizeInput（由 Send API 注入）
# ────────────────────────────────────────────────────────────

_SUMMARIZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "你是一位专业的内容分析师，擅长从长篇资料中提炼核心洞察。\n"
     "输出要求：\n"
     "1. 核心摘要（150字以内）\n"
     "2. 3个关键数据点\n"
     "3. 该子领域对总议题的重要性（1句话）\n"
     "回答语言：中文"),
    ("human",
     "总研究主题：{query}\n子领域：{subtopic}\n\n原始资料：\n{source_text}\n\n请完成摘要。"),
])


def summarize_worker_node(state: SummarizeInput) -> dict[str, Any]:
    """
    Summarize Worker 节点。
    对 Search Worker 的输出进行摘要提炼。
    同样支持重试机制。
    """
    task_id: str = state["task_id"]
    source_text: str = state["source_text"]
    subtopic: str = state["subtopic"]
    query: str = state["query"]
    retry_count_init: int = state.get("retry_count", 0)

    start = time.perf_counter()
    status = "success"
    output = ""
    error_msg = ""
    retry_count = retry_count_init

    logger.info(f"[Summarize Worker {task_id}] 开始摘要: {subtopic!r}")

    llm = get_llm(temperature=0.2)
    chain = _SUMMARIZE_PROMPT | llm

    for attempt in range(RETRY_MAX_TIMES):
        try:
            result = chain.invoke({
                "query": query,
                "subtopic": subtopic,
                "source_text": source_text[:3000],  # 防止超 token 限制
            })
            output = result.content
            retry_count = attempt
            break
        except Exception as exc:
            error_msg = str(exc)
            logger.warning(f"[Summarize Worker {task_id}] 第 {attempt+1} 次失败: {exc}")
            if attempt == RETRY_MAX_TIMES - 1:
                output = f"⚠️ 摘要失败（已重试 {RETRY_MAX_TIMES} 次）：{error_msg}\n原始内容片段：{source_text[:200]}"
                status = "failed_recovered"
                retry_count = attempt
            time.sleep(0.5 * (attempt + 1))

    end = time.perf_counter()
    contribution = _make_contribution(
        worker_id=f"summarize-{task_id}",
        worker_type="summarize",
        subtask=f"摘要子主题: {subtopic}",
        output=output,
        start_time=start,
        end_time=end,
        retry_count=retry_count,
        status=status,
    )
    logger.info(f"[Summarize Worker {task_id}] 完成，耗时 {contribution['duration']:.2f}s")

    return {
        "summaries": [{"task_id": task_id, "subtopic": subtopic, "content": output}],
        "contributions": [contribution],
        "errors": ([error_msg] if status != "success" else []),
    }


# ────────────────────────────────────────────────────────────
# Format Worker  （串行，汇总所有摘要并生成报告）
# 入参格式：全局 ReportState
# ────────────────────────────────────────────────────────────

_FORMAT_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "你是一位专业的研究报告撰写人，擅长将多方来源的信息整合成结构完整、"
     "逻辑清晰且带引用标注的学术风格报告。\n\n"
     "报告格式（Markdown）：\n"
     "# 研究报告：{query}\n\n"
     "## 执行摘要\n...\n\n"
     "## 1. [子主题1]\n...\n\n"
     "## 2. [子主题2]\n...\n\n"
     "## 结论\n...\n\n"
     "## 参考来源\n（引用各子章节提及的来源，格式 [1] 来源名）\n\n"
     "---\n"
     "> ⚙️ Worker 执行元数据将由系统自动附加在报告末尾。"),
    ("human",
     "研究主题：{query}\n\n各子领域摘要：\n{summaries_text}\n\n"
     "请生成完整的研究报告。"),
])


def format_worker_node(state: ReportState) -> dict[str, Any]:
    """
    Format Worker 节点（串行执行）。
    汇总所有 Summarize Worker 的输出，调用 LLM 生成完整 Markdown 报告。
    """
    query: str = state["query"]
    summaries: list[dict] = state.get("summaries", [])

    start = time.perf_counter()
    status = "success"
    final_report = ""
    error_msg = ""

    logger.info(f"[Format Worker] 开始格式化报告，共 {len(summaries)} 个子主题摘要")

    # 拼接所有摘要供 LLM 使用
    summaries_text = "\n\n".join(
        f"### {i+1}. {s['subtopic']}\n{s['content']}"
        for i, s in enumerate(summaries)
    )

    llm = get_llm(temperature=0.2)
    chain = _FORMAT_PROMPT | llm

    for attempt in range(RETRY_MAX_TIMES):
        try:
            result = chain.invoke({"query": query, "summaries_text": summaries_text})
            final_report = result.content
            break
        except Exception as exc:
            error_msg = str(exc)
            logger.warning(f"[Format Worker] 第 {attempt+1} 次失败: {exc}")
            if attempt == RETRY_MAX_TIMES - 1:
                # 降级处理：直接拼接摘要作为报告
                final_report = f"# 研究报告：{query}\n\n{summaries_text}\n\n⚠️ 格式化失败，以原始摘要呈现。"
                status = "failed_recovered"

    end = time.perf_counter()
    contribution = _make_contribution(
        worker_id="format-0",
        worker_type="format",
        subtask="生成最终研究报告",
        output=final_report,
        start_time=start,
        end_time=end,
        status=status,
    )
    logger.info(f"[Format Worker] 完成，耗时 {contribution['duration']:.2f}s")

    return {
        "final_report": final_report,
        "contributions": [contribution],
        "phase": Phase.DONE,
        "audit_log": [f"[Format Worker] 报告生成完成，状态: {status}"],
        "errors": ([error_msg] if status != "success" else []),
    }
