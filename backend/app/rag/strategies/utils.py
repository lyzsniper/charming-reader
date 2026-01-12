"""
RAG 策略工具函数
提供缓存、日志、监控等功能
"""
import hashlib
import json
import time
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime, timedelta

# 配置日志
logger = logging.getLogger(__name__)

# 简单的内存缓存（生产环境建议使用 Redis）
_cache: Dict[str, Dict[str, Any]] = {}
_cache_ttl: Dict[str, datetime] = {}


def get_cache_key(question: str, strategy_type: str, **kwargs) -> str:
    """
    生成缓存键
    
    Args:
        question: 用户问题
        strategy_type: 策略类型
        **kwargs: 其他影响结果的参数
        
    Returns:
        str: 缓存键
    """
    # 创建包含所有相关参数的字典
    cache_data = {
        "question": question,
        "strategy_type": strategy_type,
        **kwargs
    }
    # 转换为 JSON 字符串并生成哈希
    cache_str = json.dumps(cache_data, sort_keys=True)
    return hashlib.md5(cache_str.encode()).hexdigest()


def get_cached_result(cache_key: str, ttl_seconds: int = 3600) -> Optional[Dict[str, Any]]:
    """
    从缓存获取结果
    
    Args:
        cache_key: 缓存键
        ttl_seconds: 缓存有效期（秒）
        
    Returns:
        Optional[Dict]: 缓存的结果，如果不存在或过期则返回 None
    """
    if cache_key not in _cache:
        return None
    
    # 检查是否过期
    if cache_key in _cache_ttl:
        if datetime.now() > _cache_ttl[cache_key]:
            # 缓存过期，删除
            del _cache[cache_key]
            del _cache_ttl[cache_key]
            return None
    
    logger.debug(f"Cache hit for key: {cache_key[:8]}...")
    return _cache[cache_key]


def set_cached_result(cache_key: str, result: Dict[str, Any], ttl_seconds: int = 3600):
    """
    将结果存入缓存
    
    Args:
        cache_key: 缓存键
        result: 要缓存的结果
        ttl_seconds: 缓存有效期（秒）
    """
    _cache[cache_key] = result
    _cache_ttl[cache_key] = datetime.now() + timedelta(seconds=ttl_seconds)
    logger.debug(f"Cached result for key: {cache_key[:8]}...")


def clear_cache():
    """清空所有缓存"""
    global _cache, _cache_ttl
    _cache.clear()
    _cache_ttl.clear()
    logger.info("Cache cleared")


def with_cache(ttl_seconds: int = 3600, enabled: bool = True):
    """
    缓存装饰器
    
    Args:
        ttl_seconds: 缓存有效期（秒）
        enabled: 是否启用缓存
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not enabled:
                return func(*args, **kwargs)
            
            # 生成缓存键（使用第一个参数作为 question，第二个参数作为 strategy_type）
            if len(args) >= 2:
                question = args[0]
                strategy_type = args[1] if isinstance(args[1], str) else str(args[1])
            elif len(args) >= 1:
                question = args[0]
                strategy_type = kwargs.get('strategy_type', 'default')
            else:
                question = kwargs.get('question', '')
                strategy_type = kwargs.get('strategy_type', 'default')
            
            cache_key = get_cache_key(question, strategy_type, **kwargs)
            
            # 尝试从缓存获取
            cached_result = get_cached_result(cache_key, ttl_seconds)
            if cached_result is not None:
                return cached_result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存入缓存
            if isinstance(result, dict):
                set_cached_result(cache_key, result, ttl_seconds)
            
            return result
        
        return wrapper
    return decorator


def with_logging(log_level: int = logging.INFO):
    """
    日志装饰器
    
    Args:
        log_level: 日志级别
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.log(log_level, f"Starting {func_name} with args: {args[:2]}...")
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed_time = time.time() - start_time
                logger.log(log_level, f"Completed {func_name} in {elapsed_time:.2f}s")
                return result
            except Exception as e:
                elapsed_time = time.time() - start_time
                logger.error(f"Error in {func_name} after {elapsed_time:.2f}s: {str(e)}", exc_info=True)
                raise
        
        return wrapper
    return decorator


def with_monitoring(metric_name: str = None):
    """
    性能监控装饰器
    
    Args:
        metric_name: 指标名称
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            metric = metric_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                elapsed_time = time.time() - start_time
                
                # 记录指标（这里可以集成到监控系统，如 Prometheus）
                logger.info(f"Metric: {metric}, Duration: {elapsed_time:.3f}s")
                
                # 如果结果包含性能信息，添加监控数据
                if isinstance(result, dict):
                    result['_metrics'] = result.get('_metrics', {})
                    result['_metrics'][metric] = {
                        'duration': elapsed_time,
                        'timestamp': datetime.now().isoformat()
                    }
                
                return result
            except Exception as e:
                elapsed_time = time.time() - start_time
                logger.error(f"Metric: {metric}, Duration: {elapsed_time:.3f}s, Error: {str(e)}")
                raise
        
        return wrapper
    return decorator


def format_context(context: str, max_length: int = 2000) -> str:
    """
    格式化上下文，确保不超过最大长度
    
    Args:
        context: 原始上下文
        max_length: 最大长度
        
    Returns:
        str: 格式化后的上下文
    """
    if len(context) <= max_length:
        return context
    
    # 如果超过长度，截取前部分并添加提示
    return context[:max_length] + f"\n\n[上下文已截断，原始长度: {len(context)} 字符]"


def validate_question(question: str, min_length: int = 3, max_length: int = 1000) -> bool:
    """
    验证问题是否有效
    
    Args:
        question: 用户问题
        min_length: 最小长度
        max_length: 最大长度
        
    Returns:
        bool: 是否有效
    """
    if not question or not isinstance(question, str):
        return False
    
    question = question.strip()
    if len(question) < min_length:
        logger.warning(f"Question too short: {len(question)} characters")
        return False
    
    if len(question) > max_length:
        logger.warning(f"Question too long: {len(question)} characters")
        return False
    
    return True


def sanitize_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    清理结果，移除内部字段
    
    Args:
        result: 原始结果
        
    Returns:
        Dict: 清理后的结果
    """
    cleaned = result.copy()
    # 移除以 _ 开头的内部字段（可选）
    # cleaned = {k: v for k, v in cleaned.items() if not k.startswith('_')}
    return cleaned


def estimate_tokens(text: str) -> int:
    """
    估算文本的 token 数量（简单估算）
    
    Args:
        text: 文本内容
        
    Returns:
        int: 估算的 token 数量
    """
    # 简单估算：英文约 4 个字符 = 1 token，中文约 1.5 个字符 = 1 token
    # 这里使用更保守的估算：平均 3 个字符 = 1 token
    return len(text) // 3


def check_context_quality(context: str, min_length: int = 50) -> bool:
    """
    检查上下文质量
    
    Args:
        context: 上下文内容
        min_length: 最小长度要求
        
    Returns:
        bool: 是否满足质量要求
    """
    if not context or len(context.strip()) < min_length:
        return False
    
    # 检查是否包含有效内容（不是只有空白或错误信息）
    if "Empty Response" in context or "Error" in context[:100]:
        return False
    
    return True
