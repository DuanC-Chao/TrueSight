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
    try:
        m = model.lower()
        if m.startswith("gpt-4") or m.startswith("gpt-3.5"):
            return tiktoken.encoding_for_model(model)
        if "gpt-4o" in m:
            try:
                return tiktoken.encoding_for_model("gpt-4o")
            except Exception:
                return tiktoken.get_encoding("cl100k_base")
        if "deepseek" in m:
            return AutoTokenizer.from_pretrained(
                "deepseek-ai/deepseek-llm-7b-base",
                trust_remote_code=True,
                use_fast=True,
            )
        if "jina" in m:
            return AutoTokenizer.from_pretrained("xlm-roberta-base", use_fast=True)
    except Exception as e:
        logging.error(f"获取tokenizer失败: {str(e)}")
    # Fallback
    return tiktoken.get_encoding("cl100k_base")

def count_tokens(text, model_or_tokenizer="gpt-3.5-turbo"):
    """Return the token count for the given text.

    Parameters
    ----------
    text: str
        Text to tokenize.
    model_or_tokenizer: str or tokenizer
        Either a model name or a tokenizer instance.
    """
    if not text:
        return 0

    try:
        if hasattr(model_or_tokenizer, "encode"):
            tokenizer = model_or_tokenizer
        else:
            tokenizer = get_tokenizer(str(model_or_tokenizer))

        tokens = tokenizer.encode(text)
        return len(tokens)
    except Exception as e:
        logging.error(f"计算Token失败: {str(e)}")
        return int(len(text.split()) * 1.3)
