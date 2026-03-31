import json
from .graph import app

def run_test_case(name: str, raw_input: str):
    print(f"\n{'='*20} 测试用例: {name} {'='*20}")
    print(f"输入内容: '{raw_input}'")
    
    # 构建初始 State 字典
    initial_state = {
        "raw_input": raw_input,
        "is_valid": False,
        "validation_message": "",
        "processed_content": "",
        "final_output": "",
        "node_trace": [],
        "snapshot_log": []
    }
    
    # 执行图
    final_state = app.invoke(initial_state)
    
    # 遍历最终 State 中的 snapshot_log，按节点顺序逐一打印每个快照
    print("\n--- 状态变更轨迹 (Snapshot Log) ---")
    for i, snapshot in enumerate(final_state["snapshot_log"]):
        node_name = snapshot.get("node_trace", ["Unknown"])[-1]
        print(f"\n[第 {i+1} 步节点: {node_name}] {'-'*40}")
        
        # 打印快照内除 snapshot_log 自身以外的所有字段及其值
        printable_snapshot = snapshot.copy()
        # snippet_log 已经在 nodes.py 中 _create_snapshot 时排除了，但保险起见再检查
        if "snapshot_log" in printable_snapshot:
            del printable_snapshot["snapshot_log"]
            
        for key, value in printable_snapshot.items():
            print(f"  {key:20}: {value}")
            
    # 最终单独打印 final_output作为本次运行的交付结果
    print(f"\n{'='*20} 最终交付结果 {'='*20}")
    print(final_state["final_output"])
    print(f"{'='*56}\n")

def main():
    test_cases = [
        ("正常合法输入", "这是一段长度适中且不包含非法字符的合法输入。"),
        ("空输入", ""),
        ("超短输入", "ab"),
        ("非法字符输入", "这是一段包含!非法字符的输入。"),
        ("超长输入", "这是一段非常长的输入。" * 50)
    ]
    
    for name, raw_input in test_cases:
        run_test_case(name, raw_input)

if __name__ == "__main__":
    main()
