"""
state.py - 全局状态定义
知识点:
  - TypedDict 做 LangGraph State（比 Pydantic 更轻量，原生支持 add_messages / operator.add 归约）
  - Annotated + operator.add 实现列表的追加归约（Reducer）
  - Send API 所需的子任务状态（WorkerInput）
  - 枚举类型做阶段控制（Phase enum）
"""
from __future__ import annotations

import operator
from enum import Enum
from typing import Annotated, Any
from typing_extensions import TypedDict


# ── 枚举：工作流阶段 ─────────────────────────────────────────
class Phase(str, Enum):
    """Supervisor 通过 phase 字段决定路由到哪个阶段。"""
    PLAN = "plan"            # 任务规划阶段
    SEARCH = "search"        # 并行搜集阶段
    SUMMARIZE = "summarize"  # 并行摘要阶段
    FORMAT = "format"        # 串行格式化阶段
    DONE = "done"            # 完成


# ── Worker 贡献记录 ─────────────────────────────────────────
class WorkerContribution(TypedDict):
    worker_id: str          # 唯一标识，例如 "search-0"
    worker_type: str        # "search" | "summarize" | "format"
    subtask: str            # 该 Worker 处理的子任务描述
    output_summary: str     # 输出片段摘要（前 200 字）
    start_time: float       # UNIX 时间戳
    end_time: float         # UNIX 时间戳
    duration: float         # 耗时（秒），= end_time - start_time
    retry_count: int        # 重试次数（0 表示首次成功）
    status: str             # "success" | "failed_recovered" | "failed"


# ── 并行 Worker 的子任务输入（供 Send API 使用）────────────────
class SearchInput(TypedDict):
    """传递给单个 Search Worker 的负载。"""
    task_id: str            # 唯一任务 ID
    subtopic: str           # 搜索子主题
    query: str              # 主查询（从全局 state 传入）
    retry_count: int        # 当前重试次数


class SummarizeInput(TypedDict):
    """传递给单个 Summarize Worker 的负载。"""
    task_id: str
    source_text: str        # 待摘要的原始文本
    subtopic: str
    query: str
    retry_count: int


# ── 全局图状态 ───────────────────────────────────────────────
class ReportState(TypedDict):
    """
    LangGraph 图的全局状态。
    所有节点读写这个字典。

    Annotated[list, operator.add] 是 LangGraph 的 Reducer 语法：
    多个并行节点的返回值会被自动合并（追加）而不是覆盖。
    """
    # 输入
    query: str                                    # 用户的研究主题

    # 规划阶段
    phase: Phase                                  # 当前工作流阶段
    subtopics: list[str]                          # Supervisor 拆解出的子主题列表

    # 并行搜集结果（Reducer：各 Search Worker 的结果追加到同一列表）
    search_results: Annotated[list[dict[str, Any]], operator.add]

    # 并行摘要结果（Reducer：各 Summarize Worker 的结果追加到同一列表）
    summaries: Annotated[list[dict[str, Any]], operator.add]

    # 最终报告
    final_report: str

    # 元数据：各 Worker 的执行记录（Reducer：追加）
    contributions: Annotated[list[WorkerContribution], operator.add]

    # 错误追踪
    errors: Annotated[list[str], operator.add]

    # Supervisor 审计日志
    audit_log: Annotated[list[str], operator.add]
