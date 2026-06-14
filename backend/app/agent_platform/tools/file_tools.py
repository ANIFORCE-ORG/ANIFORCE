"""
文件操作工具
"""

import os
from pathlib import Path
from typing import Dict, Any
from loguru import logger


def read_file_tool(path: str) -> str:
    """
    读取文件内容
    
    Args:
        path: 文件路径（相对于工作目录）
    
    Returns:
        文件内容
    """
    try:
        full_path = Path(path).resolve()
        
        # 安全检查：不允许读取系统敏感文件
        if not str(full_path).startswith(str(Path.cwd())):
            return f"错误：不允许读取工作目录外的文件：{path}"
        
        if not full_path.exists():
            return f"错误：文件不存在：{path}"
        
        if not full_path.is_file():
            return f"错误：路径不是文件：{path}"
        
        content = full_path.read_text(encoding='utf-8')
        logger.info(f"[TOOL] 读取文件：{path} ({len(content)} 字符)")
        return content
    
    except Exception as e:
        logger.error(f"[TOOL] 读取文件失败：{path} - {e}")
        return f"错误：读取文件失败 - {str(e)}"


def write_file_tool(path: str, content: str) -> str:
    """
    写入文件内容（覆盖模式）
    
    Args:
        path: 文件路径（相对于工作目录）
        content: 文件内容
    
    Returns:
        操作结果
    """
    try:
        full_path = Path(path).resolve()
        
        # 安全检查：不允许写入工作目录外
        if not str(full_path).startswith(str(Path.cwd())):
            return f"错误：不允许写入工作目录外的文件：{path}"
        
        # 创建父目录
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        full_path.write_text(content, encoding='utf-8')
        
        logger.info(f"[TOOL] 写入文件：{path} ({len(content)} 字符)")
        return f"成功：文件已写入 {path}"
    
    except Exception as e:
        logger.error(f"[TOOL] 写入文件失败：{path} - {e}")
        return f"错误：写入文件失败 - {str(e)}"


def list_files_tool(directory: str = ".") -> str:
    """
    列出目录下的文件和子目录
    
    Args:
        directory: 目录路径（相对于工作目录）
    
    Returns:
        文件列表（每行一个）
    """
    try:
        full_path = Path(directory).resolve()
        
        # 安全检查
        if not str(full_path).startswith(str(Path.cwd())):
            return f"错误：不允许访问工作目录外的路径：{directory}"
        
        if not full_path.exists():
            return f"错误：目录不存在：{directory}"
        
        if not full_path.is_dir():
            return f"错误：路径不是目录：{directory}"
        
        # 列出文件
        items = []
        for item in sorted(full_path.iterdir()):
            rel_path = item.relative_to(Path.cwd())
            if item.is_dir():
                items.append(f"[DIR]  {rel_path}/")
            else:
                size = item.stat().st_size
                items.append(f"[FILE] {rel_path} ({size} bytes)")
        
        result = "\n".join(items) if items else "(空目录)"
        logger.info(f"[TOOL] 列出目录：{directory} ({len(items)} 项)")
        return result
    
    except Exception as e:
        logger.error(f"[TOOL] 列出目录失败：{directory} - {e}")
        return f"错误：列出目录失败 - {str(e)}"
