"""
graph.py - LangGraph 工作流图的构建与编译
==========================================
知识点:
  1. StateGraph: LangGraph 的核心图构建器，绑定特定的 State 类型
  2. add_node(): 注册节点函数到图中
  3. add_edge(): 添加无条件边（确定性流向）
  4. add_conditional_edges(): 添加条件边，根据路由函数的返回值决定下一个节点
     - 路由函数接收 State，返回节点名称字符串或 END
     - 这是 LangGraph 实现条件分支的核心 API
  5. START / END: 图的内置起始和终止标记
  6. MemorySaver: 基于内存的 Checkpointer
     - 每次节点执行完毕后，自动序列化完整 State 快照
     - 支持按 thread_id 存储多条对话/工作流线程，互不干扰
     - interrupt() 后，State 在此时刻被持久化，等待 resume
  7. compile(checkpointer=...): 将图 + Checkpointer 绑定，返回可执行的 CompiledGraph

生产级实践:
  - 路由函数是纯函数（无副作用），便于单元测试和逻辑审查
  - 路由逻辑中优先检查循环上限（防御性编程），再检查置信度
  - 图结构可视化（get_graph().draw_mermaid()）有助于文档化和调试

工作流图结构:
  START
    │
    ▼
  [ai_moderate_node]
    │
    ▼ (条件边 route_after_ai)
    ├─── loop >= MAX → [fallback_node] → END
    ├─── result=pass AND confidence >= threshold → [approve_node] → END
    ├─── result=reject AND confidence >= threshold → [reject_node] → END
    └─── confidence < threshold OR result=needs_review
          │
          ▼
        [human_review_node] ← interrupt() 在此暂停
          │
          ▼ (条件边 route_after_human)
          ├─── decision=approve → [approve_node] → END
          ├─── decision=reject → [reject_node] → END
          └─── decision=request_ai_recheck → [ai_moderate_node] ← 循环
"""
import logging

from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import END, START
from langgraph.graph import StateGraph

from .config import settings
from .nodes import (
    ai_moderate_node,
    approve_node,
    fallback_node,
    human_review_node,
    reject_node,
)
from .state import ModerationState

logger = logging.getLogger(__name__)

# ============================================================
# 路由函数 (纯函数，无副作用)
# ============================================================

def route_after_ai(state: ModerationState) -> str:
    """
    AI 审核节点完成后的条件路由。

    路由优先级 (从高到低):
        1. 循环上限检查 (防御性，最优先)
        2. 高置信度自动判定
        3. 低置信度或需要人工复核
    """
    loop_count: int = state.get("loop_count", 0)
    ai_output = state.get("ai_output")

    logger.debug(
        f"[route_after_ai] loop_count={loop_count}, "
        f"result={ai_output.result if ai_output else 'N/A'}, "
        f"confidence={(ai_output.confidence if ai_output else 0):.2f}"
    )

    # 优先级 1: 循环上限熔断
    # 注意: loop_count 在 ai_moderate_node 内已经 +1，
    # 此时读到的值是本次执行后的累计值
    if loop_count >= settings.MAX_REVIEW_LOOPS:
        logger.warning(f"[route_after_ai] 触发循环上限，路由至 fallback | count={loop_count}")
        return "fallback_node"

    if ai_output is None:
        logger.error("[route_after_ai] ai_output 为空，路由至 fallback")
        return "fallback_node"

    # 优先级 2: 高置信度自动决策
    if ai_output.confidence >= settings.CONFIDENCE_THRESHOLD:
        if ai_output.result == "pass":
            logger.info("[route_after_ai] 高置信度通过，自动批准")
            return "approve_node"
        elif ai_output.result == "reject":
            logger.info("[route_after_ai] 高置信度拒绝，自动拒绝")
            return "reject_node"

    # 优先级 3: 低置信度或明确需要人工的情况
    logger.info(
        f"[route_after_ai] 低置信度 ({ai_output.confidence:.2f}) 或需人工审核，"
        f"路由至 human_review"
    )
    return "human_review_node"


def route_after_human(state: ModerationState) -> str:
    """
    人工审核节点完成（恢复）后的条件路由。
    根据 human_feedback.decision 决定下一步走向。
    """
    human_feedback = state.get("human_feedback")

    if human_feedback is None:
        logger.error("[route_after_human] human_feedback 为空，兜底路由至 fallback")
        return "fallback_node"

    decision = human_feedback.decision
    logger.info(f"[route_after_human] 人工决策: {decision}")

    if decision == "approve":
        return "approve_node"
    elif decision == "reject":
        return "reject_node"
    elif decision == "request_ai_recheck":
        # 循环回 AI 节点重新评估
        # 注意: route_after_ai 会在下一轮检查 loop_count，确保不会无限循环
        return "ai_moderate_node"
    else:
        logger.warning(f"[route_after_human] 未知决策: {decision}，路由至 fallback")
        return "fallback_node"


# ============================================================
# 图构建函数
# ============================================================

def build_graph() -> StateGraph:
    """
    构建未编译的 StateGraph。
    将此函数与 compile() 分离，便于测试时单独检查图结构。
    """
    graph = StateGraph(ModerationState)

    # --- 注册节点 ---
    graph.add_node("ai_moderate_node", ai_moderate_node)
    graph.add_node("human_review_node", human_review_node)
    graph.add_node("approve_node", approve_node)
    graph.add_node("reject_node", reject_node)
    graph.add_node("fallback_node", fallback_node)

    # --- 设置入口 ---
    graph.add_edge(START, "ai_moderate_node")

    # --- 条件边: AI 审核节点完成后 ---
    graph.add_conditional_edges(
        "ai_moderate_node",
        route_after_ai,
        {
            "human_review_node": "human_review_node",
            "approve_node": "approve_node",
            "reject_node": "reject_node",
            "fallback_node": "fallback_node",
        },
    )

    # --- 条件边: 人工审核节点恢复后 ---
    graph.add_conditional_edges(
        "human_review_node",
        route_after_human,
        {
            "ai_moderate_node": "ai_moderate_node",
            "approve_node": "approve_node",
            "reject_node": "reject_node",
            "fallback_node": "fallback_node",
        },
    )

    # --- 无条件终结边 ---
    graph.add_edge("approve_node", END)
    graph.add_edge("reject_node", END)
    graph.add_edge("fallback_node", END)

    return graph


def create_workflow():
    """
    编译并返回带 MemorySaver Checkpointer 的完整工作流应用。

    MemorySaver 的工作原理:
        - 每次节点执行完毕，完整的 ModerationState 快照被序列化并存入内存
        - 按 config["configurable"]["thread_id"] 分隔存储，不同线程互不影响
        - 调用 interrupt() 时，当前快照被保存，图执行暂停
        - 调用 app.invoke(Command(resume=...), config=same_thread_config) 时，
          从最新快照恢复，仅继续执行 human_review_node 中 interrupt() 之后的逻辑

    生产级注意事项:
        - 生产环境应替换为 PostgresSaver 或 SqliteSaver，实现跨进程持久化
        - thread_id 建议使用 UUID，保证全局唯一
    """
    graph = build_graph()
    checkpointer = MemorySaver()
    app = graph.compile(checkpointer=checkpointer)
    logger.info("[create_workflow] 工作流编译完成，Checkpointer: MemorySaver")
    return app


# 模块级别的默认工作流实例（单例模式，适合单进程使用）
workflow_app = create_workflow()
