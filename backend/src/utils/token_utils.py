#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Token工具模块

本模块提供Token计算相关的工具函数，支持多种模型的Token计数。
"""

import logging
from functools import lru_cache

import tiktoken
from transformers import AutoTokenizer

@lru_cache(maxsize=None)
def get_tokenizer(model: str = "gpt-3.5-turbo"):
    """Return a tokenizer instance for the given model name."""
    model_lower = (model or "").lower()
    try:
        if model_lower.startswith("gpt-4o"):
            try:
                return tiktoken.encoding_for_model("gpt-4o")
            except Exception:
                return tiktoken.get_encoding("cl100k_base")
        if model_lower.startswith("gpt-4"):
            return tiktoken.encoding_for_model("gpt-4")
        if model_lower.startswith("gpt-3.5"):
            return tiktoken.encoding_for_model("gpt-3.5-turbo")
        if "deepseek" in model_lower:
            return AutoTokenizer.from_pretrained(
                "deepseek-ai/deepseek-llm-7b-base",
                trust_remote_code=True,
                use_fast=True,
            )
        if "jina" in model_lower or "xlm-roberta" in model_lower:
            return AutoTokenizer.from_pretrained("xlm-roberta-base", use_fast=True)
    except Exception as e:
        logging.error(f"获取tokenizer失败: {e}")
    # 默认编码
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None

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
        tokenizer = model
        if isinstance(model, str):
            tokenizer = get_tokenizer(model)

        if hasattr(tokenizer, "encode"):
            tokens = tokenizer.encode(text)
            return len(tokens)
        if hasattr(tokenizer, "tokenize"):
            return len(tokenizer.tokenize(text))
        return len(text.split())
    
    except Exception as e:
        logging.error(f"计算Token失败: {str(e)}")
        # 备用方案：简单估算
        return len(text.split()) * 1.3  # 粗略估计：单词数 * 1.3

