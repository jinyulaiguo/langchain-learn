"""
错误处理模块
覆盖三类核心错误：超时、Rate Limit、无效密钥
以及网络错误、服务端错误等附加类型
"""
from enum import Enum


class ErrorType(str, Enum):
    """错误类型枚举"""
    TIMEOUT = "timeout"                  # 请求超时
    RATE_LIMIT = "rate_limit"           # 速率限制（429）
    INVALID_KEY = "invalid_key"         # 无效 API 密钥（401）
    NETWORK_ERROR = "network_error"     # 网络连接失败
    SERVER_ERROR = "server_error"       # 服务端 5xx 错误
    PERMISSION_DENIED = "permission_denied"  # 403 权限拒绝
    NOT_FOUND = "not_found"             # 404 资源不存在
    UNKNOWN = "unknown"                 # 未知错误


class LLMAPIError(Exception):
    """LLM API 调用异常基类"""

    def __init__(
        self,
        error_type: ErrorType,
        message: str,
        status_code: int | None = None,
        provider: str = "",
        raw_response: dict | None = None,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.status_code = status_code
        self.provider = provider
        self.raw_response = raw_response or {}

    def to_dict(self) -> dict:
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "status_code": self.status_code,
            "provider": self.provider,
        }

    def __repr__(self) -> str:
        return (
            f"LLMAPIError(type={self.error_type.value}, "
            f"provider={self.provider!r}, "
            f"status={self.status_code}, "
            f"msg={self.message!r})"
        )


def classify_http_error(status_code: int, response_body: dict, provider: str) -> LLMAPIError:
    """
    根据 HTTP 状态码和响应体分类错误类型

    Args:
        status_code: HTTP 响应状态码
        response_body: 解析后的响应 JSON 体
        provider: API 提供商名称

    Returns:
        对应类型的 LLMAPIError
    """
    # 提取错误消息
    error_msg = (
        response_body.get("error", {}).get("message")
        or response_body.get("error", {}).get("type")
        or str(response_body)
    )

    if status_code == 401:
        return LLMAPIError(
            error_type=ErrorType.INVALID_KEY,
            message=f"API 密钥无效或已过期: {error_msg}",
            status_code=status_code,
            provider=provider,
            raw_response=response_body,
        )
    elif status_code == 429:
        return LLMAPIError(
            error_type=ErrorType.RATE_LIMIT,
            message=f"触发速率限制，请稍后重试: {error_msg}",
            status_code=status_code,
            provider=provider,
            raw_response=response_body,
        )
    elif status_code == 403:
        return LLMAPIError(
            error_type=ErrorType.PERMISSION_DENIED,
            message=f"权限被拒绝: {error_msg}",
            status_code=status_code,
            provider=provider,
            raw_response=response_body,
        )
    elif status_code == 404:
        return LLMAPIError(
            error_type=ErrorType.NOT_FOUND,
            message=f"API 端点不存在: {error_msg}",
            status_code=status_code,
            provider=provider,
            raw_response=response_body,
        )
    elif 500 <= status_code < 600:
        return LLMAPIError(
            error_type=ErrorType.SERVER_ERROR,
            message=f"服务端错误 {status_code}: {error_msg}",
            status_code=status_code,
            provider=provider,
            raw_response=response_body,
        )
    else:
        return LLMAPIError(
            error_type=ErrorType.UNKNOWN,
            message=f"未知 HTTP 错误 {status_code}: {error_msg}",
            status_code=status_code,
            provider=provider,
            raw_response=response_body,
        )
