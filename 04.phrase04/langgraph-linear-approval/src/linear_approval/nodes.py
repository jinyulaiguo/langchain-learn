import datetime
import re
from typing import Any, Dict
from .state import ApprovalState

def _create_snapshot(state: ApprovalState) -> Dict[str, Any]:
    """创建当前状态的副本（排除 snapshot_log 自身，以防无限嵌套或冗余数据）"""
    snapshot = state.copy()
    if "snapshot_log" in snapshot:
        del snapshot["snapshot_log"]
    return snapshot

def validate_input(state: ApprovalState) -> Dict[str, Any]:
    raw_input = state.get("raw_input", "").strip()
    is_valid = True
    validation_message = "验证通过"
    
    # 验证逻辑
    if not raw_input:
        is_valid = False
        validation_message = "输入不能为空"
    elif len(raw_input) < 5:
        is_valid = False
        validation_message = f"输入长度太短 (当前: {len(raw_input)}, 最少: 5)"
    elif len(raw_input) > 500:
        is_valid = False
        validation_message = f"输入长度超出限制 (当前: {len(raw_input)}, 最多: 500)"
    elif re.search(r"[!@#$%^&*()]", raw_input): # 示例非法字符规则
        is_valid = False
        validation_message = "输入包含非法字符"
        
    # 构建更新字典
    update = {
        "is_valid": is_valid,
        "validation_message": validation_message,
        "node_trace": ["validate_input"]
    }
    
    # 计算本节点执行后的临时状态以生成快照
    temp_state = state.copy()
    temp_state.update(update)
    update["snapshot_log"] = [_create_snapshot(temp_state)]
    
    return update

def process_content(state: ApprovalState) -> Dict[str, Any]:
    is_valid = state.get("is_valid", False)
    raw_input = state.get("raw_input", "")
    
    if not is_valid:
        processed_content = "跳过处理：输入验证未通过。"
    else:
        # 模拟处理逻辑：1. 清理空白 2. 统计字数并拼接
        cleaned = " ".join(raw_input.split())
        processed_content = f"处理结果：内容已清洗。总字数：{len(cleaned)}。预览：{cleaned[:50]}..."
        
    update = {
        "processed_content": processed_content,
        "node_trace": ["process_content"]
    }
    
    temp_state = state.copy()
    temp_state.update(update)
    update["snapshot_log"] = [_create_snapshot(temp_state)]
    
    return update

def format_output(state: ApprovalState) -> Dict[str, Any]:
    is_valid = state.get("is_valid", False)
    validation_message = state.get("validation_message", "")
    processed_content = state.get("processed_content", "")
    node_trace = state.get("node_trace", []) + ["format_output"]
    
    status_icon = "✅" if is_valid else "❌"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    final_output = (
        f"--- 审批结果报告 ---\n"
        f"时间戳：{timestamp}\n"
        f"审批状态：[{status_icon}] {'通过' if is_valid else '未通过'}\n"
        f"验证说明：{validation_message}\n"
        f"处理结果：{processed_content}\n"
        f"执行轨迹：{' -> '.join(node_trace)}\n"
        f"--------------------"
    )
    
    update = {
        "final_output": final_output,
        "node_trace": ["format_output"]
    }
    
    temp_state = state.copy()
    temp_state.update(update)
    update["snapshot_log"] = [_create_snapshot(temp_state)]
    
    return update
