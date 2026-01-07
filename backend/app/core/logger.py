"""
统一的日志配置模块
提供彩色、结构化的日志输出，包含文件名、行号、函数名等详细信息
"""
import logging
import sys
from pathlib import Path
from typing import Optional
import colorlog


class LoggerConfig:
    """日志配置类"""
    
    # 日志级别
    LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    # 彩色日志格式
    COLOR_LOG_FORMAT = (
        "%(log_color)s%(levelname)-8s%(reset)s "
        "%(cyan)s%(asctime)s%(reset)s "
        "%(blue)s[%(name)s]%(reset)s "
        "%(purple)s%(filename)s:%(lineno)d%(reset)s "
        "%(green)s%(funcName)s()%(reset)s "
        "- %(message)s"
    )
    
    # 文件日志格式（不带颜色）
    FILE_LOG_FORMAT = (
        "%(levelname)-8s %(asctime)s [%(name)s] "
        "%(filename)s:%(lineno)d %(funcName)s() - %(message)s"
    )
    
    # 时间格式
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    # 颜色配置
    LOG_COLORS = {
        'DEBUG': 'white',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }
    
    @classmethod
    def setup_logger(
        cls,
        name: str,
        level: str = "INFO",
        log_file: Optional[str] = None,
        enable_console: bool = True
    ) -> logging.Logger:
        """
        配置并返回一个日志记录器
        
        Args:
            name: 日志记录器名称（通常使用 __name__）
            level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
            log_file: 日志文件路径（可选）
            enable_console: 是否启用控制台输出
        
        Returns:
            配置好的 Logger 对象
        """
        logger = logging.getLogger(name)
        logger.setLevel(cls.LEVELS.get(level.upper(), logging.INFO))
        
        # 避免重复添加 handler
        if logger.handlers:
            return logger
        
        # 控制台彩色输出
        if enable_console:
            console_handler = colorlog.StreamHandler(sys.stdout)
            console_handler.setLevel(cls.LEVELS.get(level.upper(), logging.INFO))
            
            color_formatter = colorlog.ColoredFormatter(
                cls.COLOR_LOG_FORMAT,
                datefmt=cls.DATE_FORMAT,
                log_colors=cls.LOG_COLORS,
                secondary_log_colors={},
                style='%'
            )
            console_handler.setFormatter(color_formatter)
            logger.addHandler(console_handler)
        
        # 文件输出（如果指定）
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别
            
            file_formatter = logging.Formatter(
                cls.FILE_LOG_FORMAT,
                datefmt=cls.DATE_FORMAT
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        # 防止日志传播到父记录器
        logger.propagate = False
        
        return logger


# 创建默认的应用日志记录器
def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    获取日志记录器的便捷函数
    
    Args:
        name: 通常传入 __name__
        level: 日志级别
    
    Returns:
        配置好的 Logger 对象
    
    使用示例:
        from core.logger import get_logger
        
        logger = get_logger(__name__)
        logger.info("这是一条信息日志")
        logger.debug("这是一条调试日志")
        logger.warning("这是一条警告日志")
        logger.error("这是一条错误日志")
    """
    # 从环境变量读取日志级别
    import os
    env_level = os.getenv("LOG_LEVEL", level).upper()
    
    # 判断是否需要输出到文件
    log_file = os.getenv("LOG_FILE")
    
    return LoggerConfig.setup_logger(
        name=name,
        level=env_level,
        log_file=log_file,
        enable_console=True
    )


# 为不同模块创建专用日志记录器工厂
class LoggerFactory:
    """日志记录器工厂"""
    
    @staticmethod
    def get_api_logger(module_name: str) -> logging.Logger:
        """API 层日志记录器"""
        return get_logger(f"api.{module_name}")
    
    @staticmethod
    def get_service_logger(module_name: str) -> logging.Logger:
        """Service 层日志记录器"""
        return get_logger(f"service.{module_name}")
    
    @staticmethod
    def get_dao_logger(module_name: str) -> logging.Logger:
        """DAO 层日志记录器"""
        return get_logger(f"dao.{module_name}")
    
    @staticmethod
    def get_rag_logger(module_name: str) -> logging.Logger:
        """RAG 模块日志记录器"""
        return get_logger(f"rag.{module_name}")
    
    @staticmethod
    def get_agent_logger(module_name: str) -> logging.Logger:
        """Agent 模块日志记录器"""
        return get_logger(f"agent.{module_name}")


# 日志装饰器：自动记录函数调用
import functools
import time
from typing import Callable


def log_execution(logger: Optional[logging.Logger] = None):
    """
    函数执行日志装饰器
    自动记录函数的调用、参数、返回值和执行时间
    
    使用示例:
        @log_execution(logger)
        def my_function(arg1, arg2):
            return arg1 + arg2
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 使用传入的 logger 或创建新的
            _logger = logger or get_logger(func.__module__)
            
            # 记录函数调用
            _logger.debug(f"调用函数: {func.__name__}")
            _logger.debug(f"参数: args={args}, kwargs={kwargs}")
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                _logger.debug(f"函数 {func.__name__} 执行成功，耗时: {elapsed:.3f}秒")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                _logger.error(
                    f"函数 {func.__name__} 执行失败，耗时: {elapsed:.3f}秒，"
                    f"错误: {type(e).__name__}: {str(e)}"
                )
                raise
        
        return wrapper
    return decorator


# 异步函数日志装饰器
def log_async_execution(logger: Optional[logging.Logger] = None):
    """
    异步函数执行日志装饰器
    
    使用示例:
        @log_async_execution(logger)
        async def my_async_function(arg1, arg2):
            return arg1 + arg2
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            _logger = logger or get_logger(func.__module__)
            
            _logger.debug(f"调用异步函数: {func.__name__}")
            _logger.debug(f"参数: args={args}, kwargs={kwargs}")
            
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time
                _logger.debug(f"异步函数 {func.__name__} 执行成功，耗时: {elapsed:.3f}秒")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                _logger.error(
                    f"异步函数 {func.__name__} 执行失败，耗时: {elapsed:.3f}秒，"
                    f"错误: {type(e).__name__}: {str(e)}"
                )
                raise
        
        return wrapper
    return decorator

