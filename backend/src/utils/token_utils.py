#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Token工具模块

本模块提供Token计算相关的工具函数，支持多种模型的Token计数。
"""

import logging
from typing import Union

import tiktoken


def get_tokenizer(model: str = "gpt-3.5-turbo"):
    """根据模型名称返回对应的tokenizer。

    Args:
        model: 模型名称

    Returns:
        tiktoken.Encoding 实例
    """
    try:
        if model.startswith("gpt-4"):
            return tiktoken.encoding_for_model("gpt-4")
        elif model.startswith("gpt-3.5"):
            return tiktoken.encoding_for_model("gpt-3.5-turbo")
        elif "qwen" in model.lower() or "deepseek" in model.lower() \
                or "gemini" in model.lower() or "mistral" in model.lower():
            # 这些模型均使用与 cl100k_base 兼容的编码
            return tiktoken.encoding_for_model("cl100k_base")
        else:
            return tiktoken.get_encoding("cl100k_base")
    except Exception as e:
        logging.error(f"获取tokenizer失败: {str(e)}")
        return tiktoken.get_encoding("cl100k_base")

def count_tokens(text: str, tokenizer_or_model: Union[str, "tiktoken.Encoding"] = "gpt-3.5-turbo"):
    """
    计算文本的Token数量
    
    Args:
        text: 文本内容
        tokenizer_or_model: 可以是模型名称或已初始化的tokenizer
        
    Returns:
        token_count: Token数量
    """
    if not text:
        return 0
    
    try:
        if hasattr(tokenizer_or_model, "encode"):
            # 已经是tokenizer实例
            encoding = tokenizer_or_model
        else:
            encoding = get_tokenizer(str(tokenizer_or_model))
        
        # 计算Token数量
        tokens = encoding.encode(text)
        return len(tokens)
    
    except Exception as e:
        logging.error(f"计算Token失败: {str(e)}")
        # 备用方案：简单估算
        return len(text.split()) * 1.3  # 粗略估计：单词数 * 1.3
