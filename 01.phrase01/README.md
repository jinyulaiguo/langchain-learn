# LLM API 调用基准测试器

## 项目目标

阶段 0 验证项目——直接调用 OpenAI / Anthropic 原始 REST API，无任何 SDK 封装。  
通过此项目验证：Python 异步编程、HTTP 客户端、环境变量管理、错误处理、结构化 JSON 输出。

## 项目结构

```
01.Phrase01/
├── run_benchmark.py                    # 主入口
├── .env                                # API 密钥（不提交 git）
├── .env.example                        # 密钥配置示例
├── benchmark_results/                  # JSON 报告输出目录（自动创建）
├── tests/
│   └── test_benchmark.py              # 单元测试
└── src/lang_series_project/benchmark/
    ├── __init__.py
    ├── config.py       # 从 .env 读取配置（无 python-dotenv 依赖）
    ├── errors.py       # 错误类型定义与 HTTP 状态码分类器
    ├── models.py       # 结构化数据模型（dataclass）
    ├── client.py       # 原始 REST 客户端（同步 + 异步）
    ├── runner.py       # 测试运行器与报告生成
    └── error_tests.py  # 错误覆盖率验证模块
```

## 快速开始

### 1. 配置 API 密钥

```bash
# .env 文件已存在，填入真实密钥
DEEPSEEK_API_KEY=sk-xxxx          # 支持 OpenAI 兼容接口
# OPENAI_API_KEY=sk-xxxx          # 可选
# ANTHROPIC_API_KEY=sk-ant-xxxx   # 可选
```

### 2. 运行基准测试

```bash
# 基本测试
uv run python run_benchmark.py

# 携带错误处理验证
uv run python run_benchmark.py --error-tests

# 自定义参数
uv run python run_benchmark.py \
  --prompt "什么是神经网络？" \
  --concurrent 5 \
  --output-dir my_results

# 查看帮助
uv run python run_benchmark.py --help
```

### 3. 运行单元测试

```bash
uv run python -m pytest tests/test_benchmark.py -v
```

## 验收标准

| 要求 | 状态 |
|------|------|
| 无 LangChain 依赖，可独立运行 | ✅ 仅依赖 `httpx` |
| 直接调用原始 REST API | ✅ 无 SDK 封装 |
| 同步与异步两种模式 | ✅ `httpx.Client` + `httpx.AsyncClient` |
| 响应时间对比输出 | ✅ 含加速比（speedup_ratio） |
| 从 .env 读取密钥 | ✅ 手动解析，无需 python-dotenv |
| 超时错误处理 | ✅ `httpx.TimeoutException` |
| Rate Limit 错误处理 | ✅ HTTP 429 分类 |
| 无效密钥错误处理 | ✅ HTTP 401 分类 |
| 结构化 JSON 报告 | ✅ 含 token 用量与延迟数据 |
| 错误处理覆盖率可验证 | ✅ `--error-tests` 参数 + 单元测试 |

## JSON 报告示例

```json
{
  "benchmark_id": "a1b2c3d4",
  "created_at": "2025-01-01T00:00:00+00:00",
  "test_prompt": "请用一句话解释什么是机器学习。",
  "concurrent_requests": 3,
  "providers": [
    {
      "provider": "deepseek",
      "model": "deepseek-chat",
      "summary": {
        "sync_avg_latency_ms": 2341.5,
        "async_avg_latency_ms": 1203.2,
        "sync_success_rate": 1.0,
        "async_success_rate": 1.0,
        "speedup_ratio": 1.95
      },
      "sync_results": [...],
      "async_results": [...]
    }
  ]
}
```

## 错误类型覆盖

| 错误类型 | 触发条件 | ErrorType 值 |
|----------|----------|--------------|
| 超时 | 响应时间超过 `timeout` | `timeout` |
| Rate Limit | HTTP 429 | `rate_limit` |
| 无效密钥 | HTTP 401 | `invalid_key` |
| 权限拒绝 | HTTP 403 | `permission_denied` |
| 服务端错误 | HTTP 5xx | `server_error` |
| 网络失败 | 连接被拒绝 | `network_error` |
| 未知 | 其他状态码 | `unknown` |
