# 多代理研究报告生成系统

> **LangGraph 多代理 & 复杂工作流 验证项目**
> 基于 Python 3.13 + LangGraph + DeepSeek

## 🎯 系统架构

```
用户输入 (query)
    │
    ▼
┌───────────────────────────────────────────────┐
│             Supervisor (调度中枢)              │
│  ① supervisor_plan   任务规划，拆解子主题      │
│  ② supervisor_search_dispatch  并行调度搜索    │
│  ③ supervisor_summarize_dispatch 并行调度摘要  │
└───────────────────────────────────────────────┘
         │                          │
         ▼ (Send API 并行)         ▼ (Send API 并行)
┌─────────────────┐      ┌─────────────────────┐
│ Search Worker×N │      │ Summarize Worker×N  │
│ (并行，独立搜索) │      │ (并行，独立摘要)     │
└─────────────────┘      └─────────────────────┘
         │                          │
         └──────────┬───────────────┘
                    ▼
             ┌──────────────┐
             │ Format Worker│ (串行，汇总报告)
             └──────────────┘
                    │
                    ▼
               最终研究报告
```

### Worker 职责

| Worker | 类型 | 执行模式 | 职责 |
|--------|------|----------|------|
| Search Worker | 专项搜集 | **并行**（Send API）| 针对每个子主题进行信息检索 |
| Summarize Worker | 专项摘要 | **并行**（Send API）| 对搜索内容提炼核心洞察 |
| Format Worker | 专项排版 | 串行 | 汇总所有摘要，生成完整报告 |

## 🔑 LangGraph 知识点覆盖

| 知识点 | 实现位置 | 说明 |
|--------|---------|------|
| `TypedDict` 状态定义 | `src/state.py` | 全局图状态，支持类型检查 |
| `Annotated[list, operator.add]` Reducer | `src/state.py` | 并行节点结果自动合并 |
| `Send` API 并行调度 | `src/supervisor.py` | 同时启动 N 个 Worker 实例 |
| `add_conditional_edges` | `src/graph.py` | 动态路由，支持返回 `list[Send]` |
| `MemorySaver` 持久化 | `src/graph.py` | 每次执行有唯一 `thread_id`，可审计 |
| `graph.stream()` 事件流 | `main.py` | 实时追踪每个节点的执行状态 |
| `graph.get_state()` 状态快照 | `main.py` | 执行完毕读取最终状态 |
| Worker 重试机制 | `src/workers.py` | `try-except` + 指数退避 |
| Phase 枚举路由 | `src/state.py`, `src/supervisor.py` | 阶段驱动的工作流控制 |

## 🚀 快速开始

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入您的 DeepSeek API Key
```

### 2. 运行（默认主题）

```bash
uv run python main.py
```

### 3. 自定义研究主题

```bash
uv run python main.py --query "量子计算在密码学领域的影响与挑战"
```

### 4. 不打印图结构（更简洁）

```bash
uv run python main.py --query "你的研究主题" --no-graph
```

## 📂 项目结构

```
multi_agent_report/
├── .env                  # 环境变量（API Key 等）
├── .env.example          # 环境变量模板
├── main.py               # 系统入口
├── pyproject.toml        # 项目依赖（uv 管理）
└── src/
    ├── __init__.py
    ├── config.py         # LLM 配置（DeepSeek）
    ├── state.py          # 全局状态定义（TypedDict + Reducer）
    ├── workers.py        # 三个 Worker 代理实现
    ├── supervisor.py     # Supervisor 调度逻辑 + Send API
    ├── graph.py          # LangGraph 图构建
    └── reporter.py       # Rich 终端报告渲染
```

## ✅ 验收标准检查

- [x] **1 个 Supervisor + 3 个 Worker**：规划/搜索调度/摘要调度/格式化各司其职
- [x] **Worker 不直接通信**：全部通过 Supervisor 节点中转
- [x] **至少 2 个 Worker 并行**：Search + Summarize 两个阶段均使用 Send API 并行
- [x] **故障重试机制**：每个 Worker 内置 try-except + 重试计数，降级输出
- [x] **执行时间与贡献标注**：`contributions` 字段记录每个 Worker 的耗时和输出摘要
- [x] **Supervisor 调度可审计**：`audit_log` 字段记录每次调度决策
- [x] **并行时间对比数据**：`reporter.py` 自动计算串行假设耗时 vs 实际并行耗时 + 加速比
