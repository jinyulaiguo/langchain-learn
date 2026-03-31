# 多模板问答路由器 (Phase 02)

本项目用于验证 LangChain 的核心概念：如何利用 **LCEL (LangChain Expression Language)** 构建灵活的 LLM 工作流。

## 项目目标

1. **掌握 Runnable 协议**：理解 `invoke`, `batch`, `stream` 等标准接口。
2. **多模板动态切换**：演示如何根据用户输入的意图（Intent）选择最合适的 Prompt 模板。
3. **弃用传统 `|` 语法**：遵循 LangChain 最新最佳实践，显式使用 `RunnableSequence` 或自定义封装。
4. **结构化处理**：将 LLM 的原始响应通过解析器（Parser）转化为业务所需的格式。

## 场景逻辑 (Routing Logic)

根据用户提问，系统会判断属于以下哪种分类并路由：
- **学术研究 (Scholar)**：侧重严谨、深度的解释。
- **幽默风趣 (Humorous)**：侧重互动感和生活化。
- **默认 (Standard)**：通用助手回复。

---

## `uv` 依赖管理与运行方式

本项目使用现代高效的 `uv` 工具进行依赖管理。

### 1. 配置环境变量
确保复制预置的环境变量模板并填写正确的 API Key：
```bash
cp .env.example .env
```

### 2. 同步依赖
```bash
uv sync
```

### 3. 运行代码
```bash
uv run python main.py
```

## 面向对象的核心接口
- `PromptTemplate`: 管理不同场景的 Prompt。
- `ChatModel`: 对接不同的模型服务（如 DeepSeek, OpenAI）。
- `Router`: 实现 `(state) -> selected_branch` 的核心导航逻辑。
