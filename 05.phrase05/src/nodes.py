"""
nodes.py - 工作流核心节点实现
==============================
知识点:
  1. 节点函数签名: 必须接收 State 并返回 State 的局部更新（dict），LangGraph 会将其 merge 到全局 State
  2. with_structured_output(): 约束 LLM 返回特定 Pydantic 模型，底层使用 tool_call 机制
  3. interrupt(): LangGraph >= 0.2 提供的原生人工介入机制
     - 调用时立即暂停节点执行，将控制权交还给调用方
     - 调用方通过 Command(resume=...) 恢复，resume 的值即为 interrupt() 的返回值
     - 与 Checkpointer 配合，断点状态完整保存，恢复时不重跑已完成节点
  4. LangChain 消息对象: 使用 HumanMessage/SystemMessage/AIMessage 结构化 LLM 调用历史

生产级实践:
  - 每个节点职责单一，对 State 的修改范围最小化
  - ai_moderate_node 捕获 LLM 调用异常，防止单次失败导致整个流程崩溃
  - human_review_node 使用 interrupt() 而非 input() / 外部轮询，是生产 HIL 的标准做法
  - fallback_node 提供明确的兜底语义，避免工作流无限挂起
"""
import json
import logging
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.types import interrupt

from .config import settings
from .state import AIModerationOutput, HumanReviewDecision, ModerationState

logger = logging.getLogger(__name__)

# ============================================================
# LLM 客户端初始化
# 使用 langchain-openai 的 ChatOpenAI，通过 base_url 指向 DeepSeek API
# DeepSeek 兼容 OpenAI 的 API 格式，因此可直接复用
# ============================================================
def _get_llm() -> ChatOpenAI:
    """懒加载 LLM 客户端，避免模块导入时就强制要求 API Key 存在"""
    return ChatOpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        model=settings.DEEPSEEK_MODEL,
        temperature=0.1,  # 审核场景需要稳定输出，低温度
        max_retries=2,
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# 节点 1: AI 自动审核节点
# ============================================================
def ai_moderate_node(state: ModerationState) -> dict:
    """
    AI 审核节点 - 调用 DeepSeek 模型对内容进行风险评估。

    State 读取:
        - content: 待审核的文本
        - human_feedback: 前一轮人工审核的意见（如果有），作为上下文提供给 LLM

    State 写入:
        - ai_output: 本次审核结果 (AIModerationOutput)
        - loop_count: +1 (触发累加 reducer)
        - messages: 追加一条审核日志
    """
    logger.info(f"[ai_moderate] 开始第 {state.get('loop_count', 0) + 1} 轮 AI 审核")

    llm = _get_llm()
    # with_structured_output: 底层使用 function_call/tool_call，强制 LLM 按 Pydantic schema 输出
    structured_llm = llm.with_structured_output(AIModerationOutput, method="function_calling")

    # 构建系统提示词
    system_prompt = """你是一个专业的内容审核 AI，请对用户提交的内容进行风险评估。

审核维度包括但不限于:
- 违法违规内容（涉黄、涉赌、涉毒）
- 仇恨言论或歧视性内容
- 垃圾广告和营销推广
- 虚假信息或误导性内容
- 政治敏感内容

请严格按照要求的格式输出审核结果，确保 confidence 字段真实反映你的把握程度。
如果内容存在模糊地带，请主动将 confidence 调低（低于 0.8），并将 result 设置为 needs_review。"""

    # 构建用户消息，若有前轮人工反馈，注入上下文
    human_context = ""
    prev_feedback: HumanReviewDecision | None = state.get("human_feedback")
    if prev_feedback:
        human_context = f"""
[上一轮人工审核意见]
决策: {prev_feedback.decision}
备注: {prev_feedback.comment}

请结合以上人工意见，重新进行更谨慎的评估。
"""

    user_message = f"""请审核以下内容:

---
{state['content']}
---
{human_context}"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]

    try:
        ai_output: AIModerationOutput = structured_llm.invoke(messages)
        logger.info(
            f"[ai_moderate] 审核完成 | result={ai_output.result} | "
            f"confidence={ai_output.confidence:.2f}"
        )

        log_entry = {
            "timestamp": _now_iso(),
            "node": "ai_moderate",
            "loop": state.get("loop_count", 0) + 1,
            "result": ai_output.result,
            "confidence": ai_output.confidence,
            "risk_flags": ai_output.risk_flags,
        }

        return {
            "ai_output": ai_output,
            "loop_count": 1,  # 触发 _add_int reducer，实际效果是 +1
            "human_feedback": None,  # 清空上一轮人工反馈
            "messages": [log_entry],
        }

    except Exception as e:
        logger.error(f"[ai_moderate] LLM 调用失败: {e}")
        # 异常情况下创建一个低置信度的 fallback 输出，让路由决策兜底处理
        fallback_output = AIModerationOutput(
            result="needs_review",
            confidence=0.0,
            reasoning=f"LLM 调用异常，需要人工介入: {str(e)}",
            risk_flags=["system_error"],
        )
        return {
            "ai_output": fallback_output,
            "loop_count": 1,
            "messages": [{"timestamp": _now_iso(), "node": "ai_moderate", "error": str(e)}],
        }


# ============================================================
# 节点 2: 人工审核节点（Human-in-the-Loop 核心）
# ============================================================
def human_review_node(state: ModerationState) -> dict:
    """
    人工审核节点 - 使用 interrupt() 暂停执行，等待外部人工输入。

    核心机制:
        interrupt(payload) 会立即中断当前节点，将 payload 作为挂起状态的元数据
        暴露给调用方。配合 Checkpointer，此时的完整 State 被持久化保存。

        调用方通过 app.invoke(Command(resume=<decision_dict>), config=...) 恢复执行。
        interrupt() 的返回值即为 Command.resume 提供的值。

    State 读取:
        - ai_output: AI 审核结果（展示给人工审核者）

    State 写入:
        - human_feedback: 人工提供的 HumanReviewDecision
        - messages: 追加一条人工审核日志
    """
    ai_output: AIModerationOutput = state["ai_output"]

    logger.info(
        f"[human_review] 触发人工审核中断 | AI 结论: {ai_output.result} | "
        f"置信度: {ai_output.confidence:.2f}"
    )

    # 准备展示给审核员的上下文信息（作为 interrupt 的 payload）
    review_context = {
        "message": "⚠️  需要人工审核，请提供决策",
        "content_to_review": state["content"],
        "ai_assessment": {
            "result": ai_output.result,
            "confidence": ai_output.confidence,
            "reasoning": ai_output.reasoning,
            "risk_flags": ai_output.risk_flags,
        },
        "loop_count": state.get("loop_count", 1),
        "max_loops": settings.MAX_REVIEW_LOOPS,
        "instructions": (
            "请提供 JSON 格式的决策: "
            '{"decision": "approve|reject|request_ai_recheck", "comment": "备注"}'
        ),
    }

    # ✨ 核心: interrupt() 调用
    # 执行到此处时，节点立即暂停
    # review_context 被作为中断元数据保存到 Checkpoint
    # 恢复时，human_input 将等于 Command(resume=...) 提供的值
    human_input = interrupt(review_context)

    # ---- 恢复执行后，以下代码继续运行 ----
    logger.info(f"[human_review] 收到人工输入: {human_input}")

    # 解析人工输入（支持 dict 直接传入 或 JSON 字符串）
    if isinstance(human_input, dict):
        decision_data = human_input
    elif isinstance(human_input, str):
        try:
            decision_data = json.loads(human_input)
        except json.JSONDecodeError:
            logger.warning(f"[human_review] 输入格式非法，使用默认拒绝决策")
            decision_data = {"decision": "reject", "comment": f"输入格式非法: {human_input}"}
    else:
        decision_data = {"decision": "reject", "comment": "未知输入类型"}

    try:
        human_decision = HumanReviewDecision(**decision_data)
    except Exception as e:
        logger.warning(f"[human_review] 决策解析失败: {e}，使用默认拒绝")
        human_decision = HumanReviewDecision(decision="reject", comment=f"解析失败: {e}")

    log_entry = {
        "timestamp": _now_iso(),
        "node": "human_review",
        "decision": human_decision.decision,
        "comment": human_decision.comment,
    }

    return {
        "human_feedback": human_decision,
        "messages": [log_entry],
    }


# ============================================================
# 节点 3: 最终通过节点
# ============================================================
def approve_node(state: ModerationState) -> dict:
    """
    内容自动通过节点。
    当 AI 置信度超过阈值 或 人工批准时触发。
    """
    ai_output: AIModerationOutput = state["ai_output"]
    human_feedback: HumanReviewDecision | None = state.get("human_feedback")

    if human_feedback and human_feedback.decision == "approve":
        reason = f"人工审核批准。审核意见: {human_feedback.comment}"
    else:
        reason = (
            f"AI 自动通过 | 置信度: {ai_output.confidence:.2f} > "
            f"阈值: {settings.CONFIDENCE_THRESHOLD} | 理由: {ai_output.reasoning}"
        )

    logger.info(f"[approve] 内容通过 | {reason}")

    return {
        "final_decision": "approved",
        "final_reason": reason,
        "messages": [{"timestamp": _now_iso(), "node": "approve", "reason": reason}],
    }


# ============================================================
# 节点 4: 最终拒绝节点
# ============================================================
def reject_node(state: ModerationState) -> dict:
    """
    内容拒绝节点。
    当 AI 高置信度判定为 reject 或 人工拒绝时触发。
    """
    ai_output: AIModerationOutput = state["ai_output"]
    human_feedback: HumanReviewDecision | None = state.get("human_feedback")

    if human_feedback and human_feedback.decision == "reject":
        reason = f"人工审核拒绝。审核意见: {human_feedback.comment}"
    else:
        reason = (
            f"AI 自动拒绝 | 置信度: {ai_output.confidence:.2f} | "
            f"风险标记: {ai_output.risk_flags} | 理由: {ai_output.reasoning}"
        )

    logger.info(f"[reject] 内容拒绝 | {reason}")

    return {
        "final_decision": "rejected",
        "final_reason": reason,
        "messages": [{"timestamp": _now_iso(), "node": "reject", "reason": reason}],
    }


# ============================================================
# 节点 5: 兜底节点（Circuit Breaker）
# ============================================================
def fallback_node(state: ModerationState) -> dict:
    """
    兜底节点 - 当循环次数超过 MAX_REVIEW_LOOPS 时触发。

    生产级实践:
        这是 Circuit Breaker（熔断器）模式的实现。防止因内容极度模糊或人工
        反复要求重新审核而导致工作流无限循环，消耗大量 LLM token 和时间。
        超过上限后，系统做出保守决策（此处默认为拒绝），并记录详细的兜底原因。
    """
    loop_count = state.get("loop_count", 0)
    reason = (
        f"已达到最大审核循环上限 ({loop_count}/{settings.MAX_REVIEW_LOOPS} 次)，"
        f"系统执行保守兜底策略: 拒绝通过。请人工进一步处理。"
    )

    logger.warning(f"[fallback] 触发兜底节点 | 已循环 {loop_count} 次")

    return {
        "final_decision": "fallback_rejected",
        "final_reason": reason,
        "error": f"超过最大循环次数: {loop_count}",
        "messages": [
            {
                "timestamp": _now_iso(),
                "node": "fallback",
                "loop_count": loop_count,
                "reason": reason,
            }
        ],
    }
