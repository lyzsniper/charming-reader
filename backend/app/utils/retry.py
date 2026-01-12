"""
重试工具模块
提供带指数退避的重试机制
"""
import time
import random
from typing import Callable, TypeVar, Optional, List
from functools import wraps
from core.logger import LoggerFactory

logger = LoggerFactory.get_service_logger(__name__)

T = TypeVar('T')


class RetryError(Exception):
    """重试失败错误"""
    pass


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    重试装饰器
    
    Args:
        max_attempts: 最大尝试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        exponential_base: 指数退避基数
        jitter: 是否添加随机抖动
        exceptions: 需要重试的异常类型
        on_retry: 重试时的回调函数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"函数 {func.__name__} 重试 {max_attempts} 次后仍然失败",
                            exc_info=True
                        )
                        raise RetryError(f"重试 {max_attempts} 次后失败: {str(e)}") from e
                    
                    # 计算延迟时间（指数退避）
                    delay = min(
                        base_delay * (exponential_base ** (attempt - 1)),
                        max_delay
                    )
                    
                    # 添加随机抖动
                    if jitter:
                        delay = delay * (0.5 + random.random())
                    
                    logger.warning(
                        f"函数 {func.__name__} 第 {attempt} 次尝试失败: {str(e)}，"
                        f"{delay:.2f} 秒后重试..."
                    )
                    
                    if on_retry:
                        on_retry(e, attempt)
                    
                    time.sleep(delay)
            
            # 理论上不会到达这里
            raise RetryError("重试失败")
        
        return wrapper
    return decorator


async def async_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    异步重试装饰器
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            import asyncio
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"异步函数 {func.__name__} 重试 {max_attempts} 次后仍然失败",
                            exc_info=True
                        )
                        raise RetryError(f"重试 {max_attempts} 次后失败: {str(e)}") from e
                    
                    # 计算延迟时间
                    delay = min(
                        base_delay * (exponential_base ** (attempt - 1)),
                        max_delay
                    )
                    
                    if jitter:
                        delay = delay * (0.5 + random.random())
                    
                    logger.warning(
                        f"异步函数 {func.__name__} 第 {attempt} 次尝试失败: {str(e)}，"
                        f"{delay:.2f} 秒后重试..."
                    )
                    
                    if on_retry:
                        on_retry(e, attempt)
                    
                    await asyncio.sleep(delay)
            
            raise RetryError("重试失败")
        
        return wrapper
    return decorator
