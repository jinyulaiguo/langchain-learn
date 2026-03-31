# 多模板问答路由器 (Phase 02)

符合 LangChain 基础阶段核心概念检验项目规范的设计。完全弃用 `|` 语法封装。

## `uv` 依赖管理与运行方式

本项目使用现代高效的 `uv` 工具进行依赖管理。

### 1. 创建虚拟环境
通过 `uv` 创建独立虚拟环境：
```bash
uv venv
```

### 2. 激活虚拟环境
- **MacOS/Linux**: 
  ```bash
  source .venv/bin/activate
  ```
- **Windows**: 
  ```bash
  .venv\Scripts\activate
  ```

### 3. 安装依赖包
依靠 `pyproject.toml` 极速安装并同步所有的依赖项：
```bash
uv pip install -e .
```
> *(等价于执行 `uv pip sync` 根据你项目的 pyproject 同步。你也可以随后随时使用 `uv pip install <package>` 手动热插拔新的依赖库 )*

### 4. 配置环境变量
确保复制预置的环境变量模板并填写正确的 API Key：
```bash
cp .env.example .env
```

### 5. 运行代码
运行路由系统：
```bash
python main.py
```
