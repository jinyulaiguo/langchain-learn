# 线性审批流 (Phase 04)

本项目通过 LangGraph 实现一个典型的 **人机协同 (Human-in-the-loop)** 工作流。

## 项目目标

1. **掌握 LangGraph 基础**：学习如何定义节点 (Nodes) 和边 (Edges)。
2. **实现状态持久化**：使用 `Checkpointer` (如 `MemorySaver`) 保存图在执行过程中的状态。
3. **人工介入 (Interrupt)**：学习如何使用 `interrupt()` 在特定节点暂停工作流，等待外部人工指令。
4. **断点续传 (Resume)**：学习如何基于 `thread_id` 从最近的快照恢复执行，并注入人工反馈。

## 工作流结构

1. **Drafting (草拟)**: LLM 生成初步内容。
2. **Manual Approval (人工审核)**: **[关键点]** 系统在此暂停。
3. **Execution (执行)**: 如果审核通过，则输出结果；如果驳回，则根据逻辑修正或终止。

---

## 运行方式

### 1. 同步依赖
```bash
uv sync
```

### 2. 启动工作流
```bash
uv run python main.py
```

### 3. 操作说明
- 当程序提示进入“审核状态”时，会展示当前的 State 快照。
- 重启程序或通过特定指令 (Command) 可以模拟人工反馈的输入，促使图继续运行。

## 核心 API 知识点
- `StateGraph(State)`: 定义状态模式。
- `compile(checkpointer=memory)`: 编译成带持久化能力的可执行图。
- `interrupt()`: 触发挂起逻辑。
- `thread_id`: 区分不同用户的独立对话会话。
