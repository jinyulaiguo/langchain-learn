# 多智能体报告生成系统 (Phase 06)

本项目展示了 **Supervisor (主管)** 模式下的多智能体协作架构，并利用 LangGraph 的 **Send API** 实现大规模任务并行。

## 项目目标

1. **主管模式 (Supervisor Pattern)**：由一个核心节点规划任务，分配给多个特定的工作智能体 (Workers)。
2. **动态任务并行 (Parallelism)**：使用 `Send()` API，基于规划结果动态启动 N 个并行实例（如搜索、摘要）。
3. **Reducer 合并状态**：学习如何通过状态聚合 (Reducers) 将多个并行节点的输出汇总回主状态。
4. **端到端工作流**：从需求分析、分块检索、结果摘录到最终报告格式化。

## 系统架构

- **Supervisor**: 负责子任务拆解与调度。
- **Search Worker**: 并行在网络或本地库检索信息。
- **Summarize Worker**: 并行处理检索到的片段。
- **Format Worker**: 将所有摘要整合成结构化报告。

---

## 运行方式

### 1. 同步依赖
```bash
uv sync
```

### 2. 生成报告
```bash
uv run python main.py
```

## 核心 API 知识点
- `Send(node_name, node_input)`: 动态触发后续节点。
- `Annotated[list, operator.add]`: 典型的 Reducer 模式，用于合并列表数据。
- `Phase`: 在 State 中记录当前所处的业务阶段（如规划中、搜索中、已完成）。
