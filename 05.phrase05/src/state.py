"""
state.py - 工作流状态定义
==========================
知识点:
  1. TypedDict: LangGraph 原生推荐的状态定义方式，保证类型安全
  2. Annotated + operator: 声明 reducer（归约函数），控制 State 字段的更新行为
     - 默认行为: 直接覆盖 (last-write-wins)
     - add_messages: 追加合并，专用于消息列表
  3. Pydantic BaseModel: 用于定义强类型的结构化 LLM 输出 (structured output)
  4. Optional / Literal: 提升类型约束的表达力，避免魔法字符串

生产级实践:
  - 所有字段都有精确的类型注释，避免运行时因 State 字段不一致导致的恢复失败
  - 将 LLM 输出的结构 (AIModerationOutput) 和工作流状态 (ModerationState) 分开定义
  - loop_count 使用 int 累加 reducer，保证多节点并发时计数器不会被覆盖
"""
import operator
from typing import Annotated, Any, Literal, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage


# ============================================================
# Pydantic 模型: 约束 LLM 的结构化输出 (Structured Output)
# ============================================================

class AIModerationOutput(BaseModel):
    """
    AI 审核节点返回的强类型结构体。
    LangGraph 中通过 llm.with_structured_output(AIModerationOutput) 保证输出格式。
    """
    result: Literal["pass", "reject", "needs_review"] = Field(
        description="审核结论: pass=通过, reject=拒绝, needs_review=需要人工审核"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="对当前审核结论的置信度, 范围 [0.0, 1.0]"
    )
    reasoning: str = Field(
        description="做出此判断的理由和依据，便于人工审核时参考"
    )
    risk_flags: list[str] = Field(
        default_factory=list,
        description="检测到的风险标记列表，例如: ['仇恨言论', '广告推广']"
    )


class HumanReviewDecision(BaseModel):
    """人工审核节点的决策结构体，用于接收外部（人工）输入"""
    decision: Literal["approve", "reject", "request_ai_recheck"] = Field(
        description="人工决策: approve=批准, reject=拒绝, request_ai_recheck=要求AI重新判断"
    )
    comment: str = Field(
        default="",
        description="人工审核意见或补充说明"
    )


# ============================================================
# TypedDict: 工作流的完整状态 (Graph State)
# ============================================================

def _add_int(a: int, b: int) -> int:
    """自定义整数累加 reducer，用于 loop_count 计数"""
    return a + b


class ModerationState(TypedDict):
    """
    内容审核工作流的完整状态定义。

    重要字段说明:
    - content: 待审核的原始文本，全程不变
    - ai_output: AI 节点每次运行后的最新审核结果
    - loop_count: 已进入 AI 审核节点的累计次数，使用累加 reducer
    - human_feedback: 人工审核后给出的决策，用于恢复执行时读取
    - final_decision: 最终裁决，由各终结节点写入
    - messages: 审核过程中的操作日志/消息记录，使用 add_messages reducer 追加
    - error: 异常或兜底原因描述
    """
    # --- 输入 ---
    content: str  # 待审核的内容

    # --- AI 节点输出 ---
    ai_output: Optional[AIModerationOutput]  # AI 审核结果

    # --- 循环控制 ---
    # Annotated[int, _add_int]: 每次更新时执行累加，而不是覆盖
    # 这是生产中防止并发节点覆盖计数器的标准做法
    loop_count: Annotated[int, _add_int]

    # --- 人工介入 ---
    # 人工提供的审核决策，interrupt 后由外部注入
    human_feedback: Optional[HumanReviewDecision]

    # --- 最终结果 ---
    final_decision: Optional[Literal["approved", "rejected", "fallback_rejected"]]
    final_reason: Optional[str]

    # --- 审计日志 ---
    # 使用 add_messages reducer，保证日志条目只追加、不覆盖
    messages: Annotated[list[Any], operator.add]

    # --- 错误信息 ---
    error: Optional[str]
