# LangChain & LangGraph 进阶学习路径 (Agent Learn)

本项目是一个系统的、循序渐进的 LangChain 与 LangGraph 学习仓库，通过 7 个阶段（Phrases）从基础 API 调用演进到复杂的生产级多智能体系统。

## 项目愿景

通过实际代码练习，掌握以下核心能力：
- **基础层**：原始 REST API 调用、异步编程、结构化输出。
- **框架层**：LangChain Expression Language (LCEL)、Runnable 协议、RAG 落地。
- **智能体层**：LangGraph 状态机、循环逻辑、人机协同 (Human-in-the-loop)。
- **架构层**：多智能体协作 (Supervisor Pattern)、并行调度、长短期记忆管理。
- **生产层**：容错机制、可观测性 (LangSmith)、性能度量。

---

## 阶段概览 (Phases)

| 阶段 | 主题 | 核心技术点 | 目录 |
| :--- | :--- | :--- | :--- |
| **Phase 01** | **API 基准测试** | `httpx` (Async), 原始 REST API, 错误处理 | [01.phrase01](./01.phrase01) |
| **Phase 02** | **LCEL 路由** | `RunnableParallel`, `PromptTemplate`, 多模板路由 | [02.phrase02](./02.phrase02) |
| **Phase 03** | **带记忆的 RAG** | `Chroma`, `WindowMemory`, 文档溯源 | [03.phrase03](./03.phrase03) |
| **Phase 04** | **线性审批流** | `LangGraph`, `interrupt`, 人工介入 | [04.phrase04/langgraph-linear-approval](./04.phrase04/langgraph-linear-approval) |
| **Phase 05** | **自我修正/反思** | 条件边 (`add_conditional_edges`), 置信度阈值 | [05.phrase05](./05.phrase05) |
| **Phase 06** | **多智能体报告** | `Supervisor`, `Send` API (并行 Worker) | [06.phrash06/multi_agent_report](./06.phrash06/multi_agent_report) |
| **Phase 07** | **韧性与监控** | `ResilienceLLM`, `LangSmith`, 链路追踪 | [07.phrase07](./07.phrase07) |

---

## 快速开始

### 1. 环境准备
项目使用 [uv](https://github.com/astral-sh/uv) 进行高效的依赖管理。

```bash
# 安装依赖并创建虚拟环境
uv sync
```

### 2. 配置密钥
在各阶段目录下或根目录创建 `.env` 文件（参考 `.env.example`）：

```env
OPENAI_API_KEY=sk-xxxx
OPENAI_BASE_URL=https://api.openai.com/v1
# 如果使用阶段 07 的监控功能
LANGSMITH_API_KEY=lsv2_pt_xxxx
```

### 3. 运行示例
进入对应目录执行：
```bash
uv run python main.py
```

## 学习建议
建议按顺序从 Phase 01 开始，每个阶段都解决了前一个阶段在复杂场景下的局限性。重点关注 LangGraph 如何通过“状态机”的思想解决传统 Chain 难以处理的循环和中途暂停问题。
