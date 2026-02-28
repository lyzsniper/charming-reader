"""
Tool call guard
提供统一的工具调用次数限制，防止无限循环
"""
from __future__ import annotations

from contextvars import ContextVar
from typing import Dict, Optional, Tuple

from core.logger import LoggerFactory

logger = LoggerFactory.get_service_logger(__name__)

# 默认每个工具允许的最大调用次数（每个会话）
MAX_CALLS_PER_TOOL = 5

# 当前会话 ID（用于区分不同对话）
_current_session_id: ContextVar[str] = ContextVar("tool_call_session_id", default="default")

# 调用计数器：key = (session_id, tool_name)
_tool_call_counts: Dict[Tuple[str, str], int] = {}


def set_current_session_id(session_id: str) -> None:
    """设置当前会话 ID（用于隔离计数）"""
    _current_session_id.set(session_id)


def reset_tool_call_counts(session_id: Optional[str] = None) -> None:
    """
    重置工具调用计数器

    Args:
        session_id: 指定会话ID（仅清除该会话计数），为空则清空全部
    """
    if session_id is None:
        if _tool_call_counts:
            logger.debug(f"重置工具调用计数器（清空 {len(_tool_call_counts)} 项）")
        _tool_call_counts.clear()
        return

    keys_to_delete = [k for k in _tool_call_counts.keys() if k[0] == session_id]
    if keys_to_delete:
        logger.debug(f"重置会话 {session_id} 的工具计数（{len(keys_to_delete)} 项）")
    for key in keys_to_delete:
        _tool_call_counts.pop(key, None)


def _get_key(tool_name: str) -> Tuple[str, str]:
    session_id = _current_session_id.get()
    return (session_id, tool_name)


def would_exceed_limit(tool_name: str, max_calls: int = MAX_CALLS_PER_TOOL) -> bool:
    """不递增计数，仅判断下一次调用是否会超限"""
    key = _get_key(tool_name)
    current = _tool_call_counts.get(key, 0)
    return current + 1 > max_calls


def check_and_increment_tool_call(
    tool_name: str,
    max_calls: int = MAX_CALLS_PER_TOOL
) -> Tuple[bool, int, Optional[str]]:
    """
    记录一次工具调用，并判断是否超限

    Returns:
        (allowed, current_count, error_message)
    """
    key = _get_key(tool_name)
    _tool_call_counts[key] = _tool_call_counts.get(key, 0) + 1
    current_count = _tool_call_counts[key]

    if current_count > max_calls:
        error_msg = (
            f"Error: Tool '{tool_name}' has been called {current_count} times "
            f"(max: {max_calls}). This indicates an infinite loop or repeated parameter errors.\n\n"
            f"Common causes:\n"
            f"1. Parameter name mismatch (e.g., using 'q' instead of 'query')\n"
            f"2. Missing required parameters\n"
            f"3. Invalid parameter values\n\n"
            f"Please review the tool documentation and use correct parameter names and values."
        )
        logger.error(f"工具 {tool_name} 调用次数超限: {current_count} > {max_calls}")
        return False, current_count, error_msg

    return True, current_count, None
