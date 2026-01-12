"""
统一异常处理模块
提供统一的错误响应格式和异常类
"""
from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from core.logger import LoggerFactory

logger = LoggerFactory.get_service_logger(__name__)


class BaseAPIException(HTTPException):
    """基础 API 异常类"""
    
    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "服务器内部错误",
        error_code: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code or f"ERR_{status_code}"
        self.extra = extra or {}


class ValidationError(BaseAPIException):
    """验证错误"""
    def __init__(self, detail: str = "请求参数验证失败", extra: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="VALIDATION_ERROR",
            extra=extra
        )


class NotFoundError(BaseAPIException):
    """资源未找到错误"""
    def __init__(self, resource: str = "资源", resource_id: Optional[str] = None):
        detail = f"{resource}不存在"
        if resource_id:
            detail += f": {resource_id}"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code="NOT_FOUND",
            extra={"resource": resource, "resource_id": resource_id} if resource_id else {"resource": resource}
        )


class UnauthorizedError(BaseAPIException):
    """未授权错误"""
    def __init__(self, detail: str = "未授权访问"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="UNAUTHORIZED"
        )


class ForbiddenError(BaseAPIException):
    """禁止访问错误"""
    def __init__(self, detail: str = "禁止访问"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="FORBIDDEN"
        )


class InternalServerError(BaseAPIException):
    """服务器内部错误"""
    def __init__(self, detail: str = "服务器内部错误", error_code: str = "INTERNAL_ERROR"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code=error_code
        )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    全局异常处理器
    统一所有异常的响应格式
    """
    # 如果是我们自定义的异常
    if isinstance(exc, BaseAPIException):
        status_code = exc.status_code
        error_code = exc.error_code
        detail = exc.detail
        extra = exc.extra
    # 如果是 FastAPI 的 HTTPException
    elif isinstance(exc, HTTPException):
        status_code = exc.status_code
        error_code = f"HTTP_{status_code}"
        detail = exc.detail
        extra = {}
    # 其他未预期的异常
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_code = "INTERNAL_ERROR"
        detail = "服务器内部错误"
        extra = {}
        # 记录未预期的异常
        logger.error(
            f"未预期的异常: {type(exc).__name__}: {str(exc)}",
            exc_info=True,
            extra={
                "path": request.url.path,
                "method": request.method,
            }
        )
    
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": error_code,
                "message": detail,
                "details": extra,
            },
            "data": None,
        }
    )


def success_response(data: Any = None, message: str = "操作成功") -> Dict[str, Any]:
    """
    统一成功响应格式
    """
    return {
        "success": True,
        "message": message,
        "data": data,
    }
