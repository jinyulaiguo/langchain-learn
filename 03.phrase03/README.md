# Phase 03: 带记忆的 RAG 问答系统

这是一个基于 LangChain 和 Chroma 的 RAG (Retrieval-Augmented Generation) 系统，具备对话记忆功能和智能路由。

## 特性

- **智能路由**：自动判断是需要检索文档还是仅基于历史对话回答。
- **对话记忆**：支持可配置长度的滑动窗口记忆。
- **来源溯源**：回答中包含准确的文档片段引用及相关性评分。
- **环境隔离**：确保检索到的上下文不会污染长期对话记忆。

## 环境要求

- **Python**: >= 3.13
- **包管理器**: [uv](https://github.com/astral-sh/uv)

## 安装与运行

1. **同步依赖**:
   ```bash
   uv sync
   ```

2. **配置环境变量**:
   在项目根目录创建 `.env` 文件并配置：
   ```env
   OPENAI_API_KEY=your_api_key_here
   OPENAI_BASE_URL=https://api.deepseek.com # 示例
   ```

3. **放置文档**:
   将 PDF 或 TXT 文档放入 `documents/` 文件夹。

4. **启动系统**:
   ```bash
   uv run main.py
   ```

## 测试

运行全量测试套件：
```bash
uv run pytest tests/ -v
```
