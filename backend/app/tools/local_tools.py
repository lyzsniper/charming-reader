"""
本地Python工具示例
用于演示Python函数工具的可调用性
"""
from typing import Dict


def echo_text(text: str) -> Dict[str, str]:
    """回显输入文本"""
    return {"echo": text}
