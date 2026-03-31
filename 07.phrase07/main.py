import os
import json
import time
from typing import Annotated, TypedDict, List, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from llm_wrapper import ResilientLLM
from infrastructure import setup_logging, metrics, set_trace_id, get_logger
from dotenv import load_dotenv

# 1. 基础设施预加载
load_dotenv()
setup_logging()
logger = get_logger()
# 初始化 LLM 包装器
llm = ResilientLLM()

# 2. 定义高度结构化的生产级状态
class State(TypedDict):
    """
    State definition for the complex AI Research Pipeline.
    Supports branch synchronization and cyclic polishing.
    """
    messages: Annotated[list, add_messages]
    research_topics: List[str]
    sections: List[str]
    quality_score: int
    iteration_count: int
    final_report: str

# 3. 核心节点实现（链路 > 10 个节点设计）

def planner_node(state: State):
    """节点 1: 策略规划"""
    logger.info("executing_node", node="planner")
    prompt = f"Based on the user query: '{state['messages'][-1].content}', plan 3 critical research areas."
    response = llm.invoke([SystemMessage(content="Professional Industry Analyst"), HumanMessage(content=prompt)])
    # 模拟从回复中提取主题
    topics = ["Market Dynamics", "Technology Barrier", "Operational Risks"]
    return {"research_topics": topics, "messages": [response], "iteration_count": 0}

def market_research_node(state: State):
    """节点 2: 市场分析"""
    logger.info("executing_node", node="market_research")
    msg = llm.invoke([HumanMessage(content=f"Analyze market trends for: {state['research_topics'][0]}")])
    return {"sections": [f"### Market Phase\n{msg.content}"]}

def technology_deepdive_node(state: State):
    """节点 3: 技术深度分析"""
    logger.info("executing_node", node="tech_dive")
    msg = llm.invoke([HumanMessage(content=f"Analyze technical roadmap for: {state['research_topics'][1]}")])
    return {"sections": [f"### Tech Roadmap\n{msg.content}"]}

def risk_assessment_node(state: State):
    """节点 4: 风险评估"""
    logger.info("executing_node", node="risk_assessment")
    msg = llm.invoke([HumanMessage(content=f"Analyze potential risks for: {state['research_topics'][2]}")])
    return {"sections": [f"### Risk Matrix\n{msg.content}"]}

def data_aggregator_node(state: State):
    """节点 5: 数据聚合"""
    logger.info("executing_node", node="aggregator")
    full_text = "\n\n".join(state["sections"])
    return {"final_report": full_text}

def synthesis_node(state: State):
    """节点 6: 综合摘要撰写"""
    logger.info("executing_node", node="synthesis")
    prompt = f"Synthesize a summary for the following research report:\n{state['final_report']}"
    msg = llm.invoke([HumanMessage(content=prompt)])
    return {"messages": [msg]}

def quality_gate_node(state: State):
    """节点 7: 质量门禁 (条件决策节点)"""
    logger.info("executing_node", node="quality_gate")
    # 第一次运行强制进入 Polish 环节以展示循环链路
    score = 95 if state["iteration_count"] >= 1 else 60
    return {"quality_score": score, "iteration_count": state["iteration_count"] + 1}

def polisher_node(state: State):
    """节点 8: 报告润色 (循环链路)"""
    logger.info("executing_node", node="polisher")
    prompt = f"Increase the professionalism of this report:\n{state['final_report'][:500]}..."
    msg = llm.invoke([SystemMessage(content="Chief Editor"), HumanMessage(content=prompt)])
    return {"messages": [msg]}

def formatter_node(state: State):
    """节点 9: 格式化输出"""
    logger.info("executing_node", node="formatter")
    # 模拟轻量格式化处理
    time.sleep(0.1) 
    return {"messages": [AIMessage(content="[Final Report Formatted for PDF/Web]")]}

def notifier_node(state: State):
    """节点 10: 状态通知"""
    logger.info("executing_node", node="notifier")
    return {"messages": [AIMessage(content="Notification sent: Report ready for Review.")]}

# 4. 路由逻辑

def router(state: State) -> Literal["polisher", "formatter"]:
    """条件路由：根据质量分决定循环还是进入下一步"""
    if state["quality_score"] > 80:
        return "formatter"
    return "polisher"

# 5. 构建图拓扑结构

builder = StateGraph(State)

# 添加所有节点
builder.add_node("planner", planner_node)
builder.add_node("market", market_research_node)
builder.add_node("tech", technology_deepdive_node)
builder.add_node("risk", risk_assessment_node)
builder.add_node("aggregator", data_aggregator_node)
builder.add_node("synthesis", synthesis_node)
builder.add_node("quality_gate", quality_gate_node)
builder.add_node("polisher", polisher_node)
builder.add_node("formatter", formatter_node)
builder.add_node("notifier", notifier_node)

# 建立链路（链式 + 循环）
builder.add_edge(START, "planner")
builder.add_edge("planner", "market")
builder.add_edge("market", "tech")
builder.add_edge("tech", "risk")
builder.add_edge("risk", "aggregator")
builder.add_edge("aggregator", "synthesis")
builder.add_edge("synthesis", "quality_gate")

# 条件循环链路
builder.add_conditional_edges(
    "quality_gate",
    router,
    {"polisher": "polisher", "formatter": "formatter"}
)

# 循环回归
builder.add_edge("polisher", "quality_gate") 

# 终点线
builder.add_edge("formatter", "notifier")
builder.add_edge("notifier", END)

# 编译图
graph = builder.compile()

# 6. 多场景模拟执行（触发 3 个独立的 LangSmith Trace）

def run_research_pipeline(query: str):
    trace_id = set_trace_id()
    print(f"\n🚀 [TRACE_ID: {trace_id}] Processing: {query}")
    
    # 增加 run_name 方便在 LangSmith 面板直接搜索
    config = {"run_name": f"Research_{query[:15]}", "recursion_limit": 50}
    
    inputs = {
        "messages": [HumanMessage(content=query)],
        "sections": [],
        "iteration_count": 0
    }
    
    for step in graph.stream(inputs, config=config):
        for node_name, output in step.items():
            print(f"  ✅ Node Finished: {node_name}")

if __name__ == "__main__":
    test_scenarios = [
        "What is DeepSeek's technical advantage?",
        "Impact of AI on semiconductor industry",
        "Future of autonomous driving in 2025"
    ]
    
    print("\n" + "!"*30)
    print("STARTING COMPLEX OBSERVABILITY SCENARIOS")
    print("Check your LangSmith Dashboard for 'Research_...' entries")
    print("!"*30 + "\n")

    for scenarios in test_scenarios:
        run_research_pipeline(scenarios)
    
    # 汇总输出
    print("\n" + "="*60)
    print("OPERATIONAL HEALTH REPORT (P50/P95 ANALYSIS)")
    print(json.dumps(metrics.get_report(), indent=2))
    print("="*60 + "\n")
