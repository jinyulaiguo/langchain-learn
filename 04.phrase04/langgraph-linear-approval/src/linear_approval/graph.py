from langgraph.graph import StateGraph, START, END
from .state import ApprovalState
from .nodes import validate_input, process_content, format_output

def build_graph():
    # 使用 StateGraph(ApprovalState) 初始化图实例
    workflow = StateGraph(ApprovalState)
    
    # 按照 validate_input → process_content → format_output 的顺序使用 add_node 注册三个节点
    workflow.add_node("validate_input", validate_input)
    workflow.add_node("process_content", process_content)
    workflow.add_node("format_output", format_output)
    
    # 使用 add_edge 连接全部节点，起点为 START，终点为 END
    # 全程只使用普通边，严格禁止 add_conditional_edges
    workflow.add_edge(START, "validate_input")
    workflow.add_edge("validate_input", "process_content")
    workflow.add_edge("process_content", "format_output")
    workflow.add_edge("format_output", END)
    
    # 调用 compile() 生成可执行的 CompiledGraph 实例
    return workflow.compile()

# 导出编译后的图
app = build_graph()
