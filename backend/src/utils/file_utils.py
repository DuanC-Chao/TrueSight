#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文件工具模块

本模块提供文件操作相关的工具函数，包括文件列表获取、内容读取、哈希计算等。
"""

import os
import hashlib
import logging
import PyPDF2
import html2text
from bs4 import BeautifulSoup

def list_files(directory, extensions=None, name_filter=None):
    """
    获取指定目录下的文件列表
    
    Args:
        directory: 目录路径
        extensions: 文件扩展名列表，如['.txt', '.pdf']
        name_filter: 文件名过滤字符串，如果文件名包含此字符串则保留
        
    Returns:
        files: 文件路径列表
    """
    files = []
    
    if not os.path.exists(directory):
        logging.warning(f"目录不存在: {directory}")
        return files
    
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            
            # 检查扩展名
            if extensions:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in extensions:
                    continue
            
            # 检查文件名过滤
            if name_filter and name_filter not in filename:
                continue
            
            files.append(file_path)
    
    return files

def read_file_content(file_path):
    """
    读取文件内容，支持txt、pdf、html格式
    
    Args:
        file_path: 文件路径
        
    Returns:
        content: 文件内容
    """
    if not os.path.exists(file_path):
        logging.error(f"文件不存在: {file_path}")
        return ""
    
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        elif ext == '.pdf':
            return read_pdf_content(file_path)
        
        elif ext == '.html':
            return read_html_content(file_path)
        
        else:
            logging.warning(f"不支持的文件格式: {ext}")
            return ""
    
    except Exception as e:
        logging.error(f"读取文件失败: {file_path}, 错误: {str(e)}")
        return ""

# 向后兼容的别名
def read_file(file_path):
    """读取文件内容的兼容函数"""
    return read_file_content(file_path)

def read_pdf_content(file_path):
    """
    读取PDF文件内容
    
    Args:
        file_path: 文件路径
        
    Returns:
        content: 文件内容
    """
    try:
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            content = ""
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                content += page.extract_text() + "\n\n"
            
            return content
    
    except Exception as e:
        logging.error(f"读取PDF文件失败: {file_path}, 错误: {str(e)}")
        return ""

def read_html_content(file_path):
    """
    读取HTML文件内容
    
    Args:
        file_path: 文件路径
        
    Returns:
        content: 文件内容
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 移除脚本和样式元素
        for script in soup(["script", "style"]):
            script.extract()
        
        # 使用html2text转换为纯文本
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.ignore_tables = False
        
        text = h.handle(str(soup))
        return text
    
    except Exception as e:
        logging.error(f"读取HTML文件失败: {file_path}, 错误: {str(e)}")
        return ""

def calculate_hash(content):
    """
    计算内容的哈希值
    
    Args:
        content: 文件内容（字节或字符串）
        
    Returns:
        hash_value: 哈希值
    """
    if isinstance(content, str):
        content = content.encode('utf-8')
    
    return hashlib.md5(content).hexdigest()

def ensure_directory(directory):
    """
    确保目录存在，如果不存在则创建
    
    Args:
        directory: 目录路径
    """
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
