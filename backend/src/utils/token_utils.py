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


@lru_cache(maxsize=4)
def get_tokenizer(model: str = "gpt-3.5-turbo"):
    """Return a tokenizer instance for the given model.

    The function tries to provide sensible defaults for several known
    models. If a specific tokenizer cannot be loaded, it falls back to
    ``cl100k_base`` from ``tiktoken`` so token counting can still
    proceed.
    """
    name = (model or "").lower()
    try:
        if name.startswith("gpt-4") or name.startswith("gpt-3.5"):
            try:
                return tiktoken.encoding_for_model(model)
            except Exception:
                return tiktoken.get_encoding("cl100k_base")
        if "gpt-4o" in name:
            return tiktoken.get_encoding("cl100k_base")
        if "deepseek" in name:
            try:
                return AutoTokenizer.from_pretrained(
                    "deepseek-ai/deepseek-llm-7b-base",
                    trust_remote_code=True,
                    use_fast=True,
                )
            except Exception as e:
                logging.error(f"获取tokenizer失败: {e}")
                return tiktoken.get_encoding("cl100k_base")
        if "jina" in name:
            try:
                return AutoTokenizer.from_pretrained(
                    "xlm-roberta-base", use_fast=True
                )
            except Exception as e:
                logging.error(f"获取tokenizer失败: {e}")
                return tiktoken.get_encoding("cl100k_base")
    except Exception as e:  # pragma: no cover - defensive
        logging.error(f"获取tokenizer失败: {e}")
    return tiktoken.get_encoding("cl100k_base")

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
        else:  # pragma: no cover - should not happen
            tokens = tokenizer.tokenize(text)

        return len(tokens)
    except Exception as e:
        logging.error(f"计算Token失败: {str(e)}")
        return int(len(text.split()) * 1.3)
