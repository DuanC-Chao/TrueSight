#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Token工具模块

本模块提供Token计算相关的工具函数，支持多种模型的Token计数。
"""

import logging
import tiktoken

def count_tokens(text, model="gpt-3.5-turbo"):
    """
    计算文本的Token数量
    
    Args:
        text: 文本内容
        model: 模型名称，用于选择合适的tokenizer
        
    Returns:
        token_count: Token数量
    """
    if not text:
        return 0
    
    try:
        # 根据模型选择合适的编码器
        if model.startswith("gpt-4"):
            encoding = tiktoken.encoding_for_model("gpt-4")
        elif model.startswith("gpt-3.5"):
            encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        elif "qwen" in model.lower():
            encoding = tiktoken.encoding_for_model("cl100k_base")  # Qwen使用类似的编码
        elif "deepseek" in model.lower():
            encoding = tiktoken.encoding_for_model("cl100k_base")  # DeepSeek使用类似的编码
        elif "gemini" in model.lower():
            encoding = tiktoken.encoding_for_model("cl100k_base")  # Gemini使用类似的编码
        elif "mistral" in model.lower():
            encoding = tiktoken.encoding_for_model("cl100k_base")  # Mistral使用类似的编码
        else:
            # 默认使用cl100k_base编码
            encoding = tiktoken.get_encoding("cl100k_base")
        
        # 计算Token数量
        tokens = encoding.encode(text)
        return len(tokens)
    
    except Exception as e:
        logging.error(f"计算Token失败: {str(e)}")
        # 备用方案：简单估算
        return len(text.split()) * 1.3  # 粗略估计：单词数 * 1.3
