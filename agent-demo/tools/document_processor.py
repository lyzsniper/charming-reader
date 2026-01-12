"""
文档处理工具 - 轻量化版本（仅内存，不依赖数据库）
"""
import os
from typing import Dict, List, Optional
from pathlib import Path
import sys
from pathlib import Path as PathLib

# 添加父目录到路径
sys.path.insert(0, str(PathLib(__file__).parent.parent))
import config

try:
    from markitdown import MarkItDown
    _md_converter = MarkItDown()
    MARKITDOWN_AVAILABLE = True
except ImportError:
    MARKITDOWN_AVAILABLE = False
    print("警告: markitdown 未安装，文件转换功能将不可用")

def simple_chunk_text(text: str, chunk_size: int = 1024, chunk_overlap: int = 100) -> List[str]:
    """
    简单的文本分块（不依赖 llama-index）
    
    Args:
        text: 要分块的文本
        chunk_size: 分块大小（字符数）
        chunk_overlap: 重叠大小（字符数）
    
    Returns:
        分块后的文本列表
    """
    if not text:
        return []
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        # 计算当前块的结束位置
        end = min(start + chunk_size, text_length)
        
        # 提取块
        chunk = text[start:end]
        
        # 尝试在句子边界处截断（如果不在最后一块）
        if end < text_length:
            # 查找最后一个句号、问号或感叹号
            last_sentence_end = max(
                chunk.rfind('。'),
                chunk.rfind('.'),
                chunk.rfind('！'),
                chunk.rfind('!'),
                chunk.rfind('？'),
                chunk.rfind('?'),
                chunk.rfind('\n')
            )
            
            if last_sentence_end > chunk_size * 0.5:  # 如果找到的边界在块的后半部分
                chunk = chunk[:last_sentence_end + 1]
                end = start + len(chunk)
        
        chunks.append(chunk.strip())
        
        # 移动到下一个块的开始位置（考虑重叠）
        start = end - chunk_overlap
        if start < 0:
            start = end
    
    return chunks

def process_document(file_path: Optional[str] = None, text: Optional[str] = None) -> Dict:
    """
    处理文档：解析、分块
    
    Args:
        file_path: 文件路径（PDF/Word/Markdown等）
        text: 直接文本输入
    
    Returns:
        {
            "markdown": str,  # Markdown格式的文档内容
            "chunks": List[str],  # 分块后的文本列表
            "chunk_count": int  # 分块数量
        }
    """
    if file_path and text:
        return {"error": "不能同时提供 file_path 和 text，请选择一种方式"}
    
    if not file_path and not text:
        return {"error": "必须提供 file_path 或 text"}
    
    # 处理文本输入
    if text:
        markdown_text = text
        chunks = simple_chunk_text(
            markdown_text,
            chunk_size=config.settings.TEST_DOCUMENT_CHUNK_SIZE,
            chunk_overlap=config.settings.TEST_DOCUMENT_CHUNK_OVERLAP
        )
        return {
            "markdown": markdown_text,
            "chunks": chunks,
            "chunk_count": len(chunks)
        }
    
    # 处理文件输入
    if not os.path.exists(file_path):
        return {"error": f"文件不存在: {file_path}"}
    
    # 检查文件扩展名
    file_ext = Path(file_path).suffix.lower()
    
    # 如果是 Markdown 文件，直接读取
    if file_ext in ['.md', '.markdown']:
        with open(file_path, 'r', encoding='utf-8') as f:
            markdown_text = f.read()
    # 如果是文本文件，直接读取
    elif file_ext in ['.txt']:
        with open(file_path, 'r', encoding='utf-8') as f:
            markdown_text = f.read()
    # 其他格式需要转换
    else:
        if not MARKITDOWN_AVAILABLE:
            return {"error": "markitdown 未安装，无法处理此文件格式。请安装: pip install markitdown"}
        
        try:
            result = _md_converter.convert(file_path)
            markdown_text = result.text_content
        except Exception as e:
            return {"error": f"文件转换失败: {str(e)}"}
    
    # 分块
    chunks = simple_chunk_text(
        markdown_text,
        chunk_size=config.settings.TEST_DOCUMENT_CHUNK_SIZE,
        chunk_overlap=config.settings.TEST_DOCUMENT_CHUNK_OVERLAP
    )
    
    return {
        "markdown": markdown_text,
        "chunks": chunks,
        "chunk_count": len(chunks)
    }
