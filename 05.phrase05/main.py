"""
main.py - 带人工介入的内容审核工作流 - 功能验证与演示
=======================================================
本脚本演示三个核心场景，验收标准完整覆盖:

  场景一: AI 高置信度自动通过/拒绝（无人工介入）
  场景二: AI 低置信度触发 interrupt → 状态持久化 → 人工输入恢复 → State 一致性验证
  场景三: 持续要求 AI 重审 → loop_count 达到上限 → 兜底节点触发

知识点:
  1. thread_id: Checkpointer 的核心隔离键，同一 thread_id 共享状态和历史快照
  2. app.stream() vs app.invoke():
     - stream(): 逐节点流式返回，便于观察执行过程
     - invoke(): 等待最终结果，适合程序化调用
  3. Command(resume=...): 向被 interrupt() 暂停的工作流注入外部输入并恢复执行
  4. app.get_state(config): 查询指定 thread 的当前 State 快照（含中断元数据）
  5. interrupt_before / interrupt_after: compile 时可静态声明中断点（高级用法）
  6. 状态一致性验证: 通过比较中断前后的 State 快照，验证恢复后节点不重跑
"""
import json
import logging
import uuid
from typing import Any

from langgraph.types import Command

from src.graph import workflow_app
from src.state import ModerationState

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


# ============================================================
# 工具函数
# ============================================================

def make_config(thread_id: str) -> dict:
    """
    构建 LangGraph 调用配置。
    thread_id 是 Checkpointer 的隔离键，同一 thread 共享状态历史。
    """
    return {"configurable": {"thread_id": thread_id}}


def pretty_state(state: ModerationState | dict, title: str = "State 快照") -> None:
    """格式化打印 State 信息"""
    print(f"\n{'='*60}")
    print(f"  📋 {title}")
    print(f"{'='*60}")

    if hasattr(state, "__getitem__"):
        data = dict(state)
    else:
        data = state

    # 核心字段优先展示
    priority_fields = [
        "content", "loop_count", "final_decision",
        "final_reason", "error"
    ]
    for field in priority_fields:
        if field in data and data[field] is not None:
            value = data[field]
            if isinstance(value, str) and len(value) > 80:
                value = value[:80] + "..."
            print(f"  {field}: {value}")

    # ai_output 单独格式化
    ai_out = data.get("ai_output")
    if ai_out:
        print(f"  ai_output:")
        if hasattr(ai_out, "model_dump"):
            for k, v in ai_out.model_dump().items():
                print(f"    - {k}: {v}")
        else:
            print(f"    {ai_out}")

    # human_feedback
    hf = data.get("human_feedback")
    if hf:
        print(f"  human_feedback:")
        if hasattr(hf, "model_dump"):
            for k, v in hf.model_dump().items():
                print(f"    - {k}: {v}")

    # 审计日志
    messages = data.get("messages", [])
    if messages:
        print(f"  messages ({len(messages)} 条):")
        for msg in messages:
            print(f"    • {msg.get('node', '?')} @ {msg.get('timestamp', '')[:19]}"
                  f" | {msg.get('result', msg.get('decision', msg.get('reason', '')))}")

    print(f"{'='*60}\n")


def run_stream(app, initial_state: dict, config: dict, label: str = "") -> Any:
    """
    流式运行工作流，逐节点打印执行信息。
    遇到 interrupt 时停止并返回 None（挂起状态）。
    正常结束时返回最终 State。
    """
    print(f"\n🚀 开始执行: {label}")
    final_state = None

    for chunk in app.stream(initial_state, config=config, stream_mode="updates"):
        for node_name, node_output in chunk.items():
            if node_name == "__interrupt__":
                # interrupt() 触发，chunk 格式为 {"__interrupt__": [Interrupt对象]}
                interrupt_data = node_output[0]
                print(f"\n⏸️  [INTERRUPT] 工作流已暂停")
                print(f"  挂起元数据:")
                if hasattr(interrupt_data, "value"):
                    payload = interrupt_data.value
                    print(f"  {json.dumps(payload, ensure_ascii=False, indent=4)}")
            else:
                print(f"  ✅ 节点执行: [{node_name}]")
                # 简单打印节点关键输出
                if "ai_output" in node_output and node_output["ai_output"]:
                    ao = node_output["ai_output"]
                    if hasattr(ao, "result"):
                        print(f"     └─ AI: result={ao.result}, confidence={ao.confidence:.2f}")
                if "final_decision" in node_output and node_output["final_decision"]:
                    print(f"     └─ 最终决策: {node_output['final_decision']}")
                if "human_feedback" in node_output and node_output["human_feedback"]:
                    hf = node_output["human_feedback"]
                    print(f"     └─ 人工决策: {hf.decision}")

    # 流结束后获取最终 State
    final_snapshot = app.get_state(config)
    return final_snapshot


# ============================================================
# 场景一: AI 高置信度自动决策（无人工介入）
# ============================================================

def scenario_1_auto_pass():
    """
    场景一验证: AI 高置信度，工作流直接自动通过或拒绝，无需 interrupt。

    验证重点:
        - START → ai_moderate_node → approve_node/reject_node → END
        - 无中断，一次性到达终态
        - final_decision 有效赋值
    """
    print("\n" + "🟢"*30)
    print("  场景一: AI 高置信度自动决策")
    print("🟢"*30)

    thread_id = f"scenario1-{uuid.uuid4().hex[:8]}"
    config = make_config(thread_id)

    # 明显安全的内容 → 期望 AI 以高置信度判定为 pass
    initial_state = {
        "content": "今天天气真好，适合去公园散步，心情愉快！",
        "loop_count": 0,
        "messages": [],
        "ai_output": None,
        "human_feedback": None,
        "final_decision": None,
        "final_reason": None,
        "error": None,
    }

    snapshot = run_stream(workflow_app, initial_state, config, "场景一")

    print(f"\n📊 执行完毕，验证结果:")
    current = snapshot.next  # 若为空，表示已到达 END
    print(f"  工作流状态: {'已完成 ✅' if not current else f'挂起于 {current}'}")
    pretty_state(snapshot.values, "最终 State")

    assert snapshot.values.get("final_decision") in ("approved", "rejected"), \
        "❌ 验证失败: final_decision 应为 approved 或 rejected"
    assert not snapshot.next, "❌ 验证失败: 工作流应已结束"
    print("  ✅ 场景一验证通过: 无中断自动完成")
    return thread_id


# ============================================================
# 场景二: 触发 interrupt → 持久化 → 人工恢复 → State 一致性验证
# ============================================================

def scenario_2_human_interrupt():
    """
    场景二验证: AI 低置信度触发 interrupt → 查验挂起 State → 人工审批 → 恢复执行。

    验证重点:
        - 工作流在 human_review_node 处暂停（snapshot.next 不为空）
        - 中断前后 content 和 loop_count 保持一致（State 一致性）
        - 恢复后仅继续执行 interrupt() 之后的逻辑，ai_moderate_node 不重跑
        - 最终 final_decision 为 approved（人工批准）
    """
    print("\n" + "🔵"*30)
    print("  场景二: 触发 interrupt + 人工恢复")
    print("🔵"*30)

    thread_id = f"scenario2-{uuid.uuid4().hex[:8]}"
    config = make_config(thread_id)

    # 模糊内容 → 期望 AI 给出低置信度，触发 interrupt
    initial_state = {
        "content": (
            "本产品采用最新量子技术，每天使用30分钟可改善睡眠质量，"
            "大量用户反馈效果显著，限时特惠仅需199元。"
        ),
        "loop_count": 0,
        "messages": [],
        "ai_output": None,
        "human_feedback": None,
        "final_decision": None,
        "final_reason": None,
        "error": None,
    }

    # --- 第一阶段: 触发中断 ---
    snapshot_before = run_stream(workflow_app, initial_state, config, "场景二-第一阶段")

    print(f"\n🔍 中断后 State 检查:")
    next_nodes = snapshot_before.next
    print(f"  工作流挂起于: {next_nodes}")

    if not next_nodes or "human_review_node" not in next_nodes:
        # AI 可能直接高置信判定，场景二自动调整演示
        print(f"\n  ⚠️  AI 以高置信度直接决策，未触发中断")
        print(f"  final_decision: {snapshot_before.values.get('final_decision')}")
        print(f"  (提示: 可调整 CONFIDENCE_THRESHOLD 环境变量来强制触发人工审核)")
        pretty_state(snapshot_before.values, "场景二 最终 State（无中断路径）")
        return thread_id

    # 记录中断前的关键 State 用于一致性对比
    state_before_resume = snapshot_before.values
    loop_count_before = state_before_resume.get("loop_count", 0)
    content_before = state_before_resume.get("content", "")

    print(f"  中断前 loop_count: {loop_count_before}")
    print(f"  中断前 content 长度: {len(content_before)} 字符")

    # --- 第二阶段: 人工注入决策，恢复执行 ---
    print(f"\n🔑 人工审核员输入决策 (approve)...")
    human_decision = {
        "decision": "approve",
        "comment": "经过人工核查，该产品描述虽有夸大，但未违规，予以通过。",
    }

    # Command(resume=...) 是 LangGraph 恢复 interrupt 的标准 API
    # 恢复时从最新 Checkpoint 读取 State，仅继续执行 interrupt() 之后的代码
    snapshot_after = run_stream(
        workflow_app,
        Command(resume=human_decision),  # resume 替代 initial_state
        config,
        "场景二-第二阶段（恢复后）",
    )

    # --- 验证 State 一致性 ---
    print(f"\n📊 State 一致性验证:")
    state_after = snapshot_after.values

    # 验证 content 未改变
    assert state_after.get("content") == content_before, \
        "❌ content 在断点恢复前后不一致！"
    print(f"  ✅ content 一致性: 通过")

    # 验证 loop_count 未因恢复而重置或额外递增
    loop_count_after = state_after.get("loop_count", 0)
    print(f"  loop_count: 中断前={loop_count_before}, 恢复后={loop_count_after}")
    assert loop_count_after == loop_count_before, \
        f"❌ loop_count 不一致（恢复后不应再次触发 ai_moderate_node）"
    print(f"  ✅ loop_count 一致性: 通过（恢复未重跑 ai_moderate_node）")

    # 验证工作流已完成
    assert not snapshot_after.next, "❌ 工作流应已完成"
    print(f"  ✅ 工作流正常结束: final_decision={state_after.get('final_decision')}")

    pretty_state(state_after, "场景二 最终 State")
    print("  ✅ 场景二验证通过: 中断恢复 State 一致性确认")
    return thread_id


# ============================================================
# 场景三: 循环上限兜底（Circuit Breaker）
# ============================================================

def scenario_3_loop_limit():
    """
    场景三验证: 人工反复要求 AI 重审 → loop_count 累加 → 达到 MAX_REVIEW_LOOPS → 兜底节点。

    验证重点:
        - loop_count 随每次 ai_moderate_node 执行精准 +1
        - 达到上限后，route_after_ai 路由至 fallback_node 而非 human_review_node
        - final_decision 为 fallback_rejected
    """
    print("\n" + "🟠"*30)
    print("  场景三: 循环上限兜底验证")
    print("🟠"*30)

    thread_id = f"scenario3-{uuid.uuid4().hex[:8]}"
    config = make_config(thread_id)

    # 使用模糊内容，期望 AI 给低置信度触发人工审核
    initial_state = {
        "content": (
            "某神秘组织声称掌握了让人延年益寿的秘方，"
            "已有数万人受益，欲加入请私信获取更多信息。"
        ),
        "loop_count": 0,
        "messages": [],
        "ai_output": None,
        "human_feedback": None,
        "final_decision": None,
        "final_reason": None,
        "error": None,
    }

    # 模拟反复要求 AI 重审（触发 3 次循环）
    # MAX_REVIEW_LOOPS 默认为 3，第 3 次 ai_moderate_node 后 loop_count=3 触发兜底
    recheck_decision = {
        "decision": "request_ai_recheck",
        "comment": "信息不足，要求 AI 重新评估。",
    }

    max_loops = 3  # 与 settings.MAX_REVIEW_LOOPS 一致
    current_config = config

    print(f"  目标: 触发 {max_loops} 次 ai_moderate_node，验证兜底节点\n")

    # 第一次调用（初始状态）
    snapshot = run_stream(workflow_app, initial_state, current_config, "场景三-初始调用")

    for loop_num in range(1, max_loops + 1):
        next_nodes = snapshot.next
        current_loop = snapshot.values.get("loop_count", 0)
        print(f"\n  [Loop {loop_num}] loop_count={current_loop}, next={next_nodes}")

        if not next_nodes:
            # 工作流已完成（可能因 AI 高置信度直接决策）
            print(f"  工作流已在第 {loop_num} 轮完成: {snapshot.values.get('final_decision')}")
            break

        if "human_review_node" in next_nodes:
            print(f"  → 触发人工审核，注入 request_ai_recheck 决策")
            snapshot = run_stream(
                workflow_app,
                Command(resume=recheck_decision),
                current_config,
                f"场景三-人工重审 #{loop_num}",
            )
        else:
            print(f"  → 工作流在意外节点暂停: {next_nodes}")
            break

    # 最终验证
    final_state = snapshot.values
    print(f"\n📊 场景三最终结果:")
    print(f"  最终 loop_count: {final_state.get('loop_count')}")
    print(f"  最终 final_decision: {final_state.get('final_decision')}")
    print(f"  error: {final_state.get('error')}")

    pretty_state(final_state, "场景三 最终 State")

    final_decision = final_state.get("final_decision")
    if final_decision == "fallback_rejected":
        print(f"  ✅ 场景三验证通过: 循环上限兜底机制有效")
    else:
        print(
            f"  ⚠️  场景三: AI 可能在某轮以高置信度自行决策（{final_decision}），"
            f"未达到兜底节点。\n"
            f"  提示: 可降低 CONFIDENCE_THRESHOLD 或使用 mock LLM 保证确定性。"
        )
    return thread_id


# ============================================================
# 附加: 打印图结构（教学用途）
# ============================================================

def print_graph_structure():
    """打印工作流的 ASCII 图结构和 Mermaid 代码，用于文档化"""
    print("\n" + "📐"*20)
    print("  工作流图结构 (Mermaid)")
    print("📐"*20)
    try:
        mermaid_code = workflow_app.get_graph().draw_mermaid()
        print(mermaid_code)
    except Exception as e:
        print(f"  (图结构输出失败: {e})")


# ============================================================
# 主入口
# ============================================================

def main():
    print("\n" + "="*60)
    print("  带人工介入的内容审核工作流 - LangGraph 阶段4 验证")
    print("="*60)

    print_graph_structure()

    # 依次运行三个验收场景
    try:
        scenario_1_auto_pass()
    except AssertionError as e:
        print(f"\n❌ 场景一 Assert 失败: {e}")

    try:
        scenario_2_human_interrupt()
    except AssertionError as e:
        print(f"\n❌ 场景二 Assert 失败: {e}")

    try:
        scenario_3_loop_limit()
    except AssertionError as e:
        print(f"\n❌ 场景三 Assert 失败: {e}")

    print("\n" + "="*60)
    print("  所有场景执行完毕")
    print("="*60)


if __name__ == "__main__":
    main()
