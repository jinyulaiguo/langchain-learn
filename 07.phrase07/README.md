# 韧性与可观测性 (Phase 07)

本项目构建了一个高度结构化的 **生产级 AI 研究流水线**，重点关注 **错误处理、容错机制 (Resilience)** 和 **全链路追踪 (Observability)**。

## 项目目标

1. **复杂图拓扑**：实现超过 10 个节点的复杂链路，包含分支同步、动态循环和条件门禁。
2. **LLM 韧性包装器 (`ResilientLLM`)**：封装重试机制 (Retry)、指数退避 (Exponential Backoff) 和备用模型 (Fallback Models)。
3. **可观测性集成**：接入 **LangSmith**，自动生成 Trace ID，捕获详细的输入输出链路。
4. **性能度量 (Metrics)**：实时记录 P50/P95 延迟、Token 消耗和各节点的健康状态。

## 流水线阶段

- **Planner**: 策略规划与拆解。
- **Research Branch**: 三个并行的研究维度（市场、技术、风险）。
- **Aggregator**: 数据聚合。
- **Quality Gate**: 报告质量门禁（循环进入 Polish 节点）。
- **Health Report**: 自动化健康报告汇总。

---

## 运行方式

### 1. 配置环境变量
确保填写 `LANGSMITH_API_KEY` 以启用监控：
```bash
cp .env.example .env
```

### 2. 同步依赖
```bash
uv sync
```

### 3. 运行流水线
```bash
uv run python main.py
```

## 核心 API 知识点
- `langgraph.graph.message.add_messages`: 管理多轮对话上下文。
- `llm.invoke(..., config={"run_name": ...})`: 为不同的运行实例命名，方便在监控面板筛选。
- `metrics.get_report()`: 自定义性能报告生成逻辑。
- `set_trace_id()`: 手动注入链路追踪 ID，实现跨系统审计。
