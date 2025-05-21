#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
URL 工具模块

本模块提供 URL 相关的工具函数，包括 URL 转换、验证等功能。
"""

import re
from urllib.parse import urlparse

def url_to_filename(url):
    """
    将 URL 转换为文件名
    
    Args:
        url: URL 字符串
        
    Returns:
        filename: 文件名
    """
    # 解析 URL
    parsed_url = urlparse(url)
    
    # 获取域名和路径
    domain = parsed_url.netloc
    path = parsed_url.path
    
    # 替换特殊字符
    domain = domain.replace('.', '_')
    
    # 处理路径
    if path and path != '/':
        # 移除开头的斜杠
        if path.startswith('/'):
            path = path[1:]
        
        # 替换特殊字符
        path = path.replace('/', '_').replace('.', '_')
        
        # 组合域名和路径
        filename = f"{domain}_{path}"
    else:
        filename = domain
    
    # 限制文件名长度
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename

def filename_to_url(filename):
    """
    将文件名转换为 URL
    
    Args:
        filename: 文件名
        
    Returns:
        url: URL 字符串，如果无法转换则返回 None
    """
    # 移除文件扩展名
    base_name = filename
    if '.' in base_name:
        base_name = base_name.rsplit('.', 1)[0]
    
    # 移除特定后缀
    if "_summarized_qa_csv" in base_name:
        base_name = base_name.replace("_summarized_qa_csv", "")
    elif "_summarized" in base_name:
        base_name = base_name.replace("_summarized", "")
    elif "_qa_json" in base_name:
        base_name = base_name.replace("_qa_json", "")
    
    # 将下划线转换为点号
    potential_url = base_name.replace('_', '.')
    
    # 验证是否为合法 URL
    if is_valid_url(potential_url):
        return potential_url
    
    return None

def is_valid_url(url):
    """
    检查字符串是否为合法 URL
    
    Args:
        url: 要检查的字符串
        
    Returns:
        bool: 是否为合法 URL
    """
    # URL 正则表达式模式
    pattern = re.compile(
        r'^(www\.)?'  # www. 是可选的
        r'(?!-)[A-Za-z0-9-]+'  # 域名部分不能以连字符开头
        r'(\.[A-Za-z0-9-]+)*'  # 子域名部分
        r'\.'  # 点号
        r'[A-Za-z]{2,}'  # 顶级域名至少2个字符
        r'(\/.*)?$'  # 路径部分是可选的
    )
    
    return bool(pattern.match(url))

def normalize_url(url):
    """
    规范化 URL
    
    Args:
        url: URL 字符串
        
    Returns:
        normalized_url: 规范化后的 URL
    """
    # 解析 URL
    parsed_url = urlparse(url)
    
    # 添加协议前缀
    if not parsed_url.scheme:
        url = f"http://{url}"
        parsed_url = urlparse(url)
    
    # 移除末尾斜杠
    path = parsed_url.path
    if path.endswith('/') and len(path) > 1:
        path = path[:-1]
    
    # 重新组合 URL
    normalized_url = f"{parsed_url.scheme}://{parsed_url.netloc}{path}"
    
    # 添加查询参数
    if parsed_url.query:
        normalized_url = f"{normalized_url}?{parsed_url.query}"
    
    # 添加片段
    if parsed_url.fragment:
        normalized_url = f"{normalized_url}#{parsed_url.fragment}"
    
    return normalized_url
