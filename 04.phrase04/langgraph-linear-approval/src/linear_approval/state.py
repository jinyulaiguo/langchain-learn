from typing import TypedDict, List, Annotated
import operator

class ApprovalState(TypedDict):
    # 用户提交的原始输入内容，由入口写入，后续节点只读
    raw_input: str
    
    # 由输入验证节点写入验证结果，初始值为 False
    is_valid: bool
    
    # 由输入验证节点写入验证的详细说明
    validation_message: str
    
    # 由内容处理节点写入经过处理后的中间结果
    processed_content: str
    
    # 由输出格式化节点写入最终交付内容
    final_output: str
    
    # 每个节点执行时向此字段追加自身节点名称，用于记录执行轨迹
    # 使用 Annotated 和 operator.add 以支持 LangGraph 的 state 合并在某些场景下的追加逻辑
    # （虽然此处是线性流可直接覆盖，但推荐这种写法以保持一致性）
    node_trace: Annotated[List[str], operator.add]
    
    # 每个节点执行结束后将当前完整 State 的副本追加至此字段
    snapshot_log: Annotated[List[dict], operator.add]
