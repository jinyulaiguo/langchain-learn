# 自我修正与反思流 (Phase 05)

本项目展示了如何使用 LangGraph 构建具备 **自我修正 (Self-correction)** 和 **反思 (Reflection)** 能力的智能审核系统。

## 项目目标

1. **条件逻辑节点**：学习如何根据 LLM 输出的置信度 (Confidence Score) 动态路由。
2. **循环审查 (Loop)**：实现 AI 与人工之间的循环纠偏，直到满足通过标准。
3. **熔断机制 (Fallback)**：设置最大循环次数，防止死循环并提供兜底方案。
4. **状态细粒度管理**：掌握如何在 Node 之间传递和更新复杂的结构化 State。

## 核心工作流

- **AI 审核节点**: 对输入内容进行安全性或合规性评分。
- **路由逻辑 (`route_after_ai`)**: 
    - 置信度 > 阈值：直接批准或拒绝。
    - 置信度 < 阈值：进入人工复核。
- **人员复核节点**: 人工介入，可选择批准、拒绝或要求 AI 重新评估。

---

## 运行方式

### 1. 同步依赖
```bash
uv sync
```

### 2. 启动系统
```bash
uv run python main.py
```

## 知识点速查
- `add_conditional_edges`: 根据函数返回值选择下一个跳转节点。
- `settings.CONFIDENCE_THRESHOLD`: 可配置的自动判定门槛。
- `loop_count`: 用于防御性编程，限制最大尝试次数。
