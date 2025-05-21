#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Token工具模块

本模块提供Token计算相关的工具函数，支持多种模型的Token计数。
"""

import logging
from typing import Union

import tiktoken

_tokenizer_cache = {}


def get_tokenizer(model: str = "gpt-3.5-turbo"):
    """Return a tokenizer for the given model name."""
    if hasattr(model, "encode"):
        return model

    if model in _tokenizer_cache:
        return _tokenizer_cache[model]

    try:
        if model.startswith("gpt-4"):
            tokenizer = tiktoken.encoding_for_model("gpt-4")
        elif model.startswith("gpt-3.5"):
            tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
        elif "qwen" in model.lower() or "deepseek" in model.lower() \
                or "gemini" in model.lower() or "mistral" in model.lower():
            tokenizer = tiktoken.encoding_for_model("cl100k_base")
        else:
            tokenizer = tiktoken.get_encoding("cl100k_base")
    except Exception:
        tokenizer = tiktoken.get_encoding("cl100k_base")

    _tokenizer_cache[model] = tokenizer
    return tokenizer

def count_tokens(text, model="gpt-3.5-turbo"):
    """Return the number of tokens for ``text`` using the given model or tokenizer."""

    if not text:
        return 0

    try:
        tokenizer = get_tokenizer(model)
        tokens = tokenizer.encode(text)
        return len(tokens)
    except Exception as e:
        logging.error(f"计算Token失败: {str(e)}")
        # fallback: rough estimation
        return int(len(text.split()) * 1.3)
