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
def get_tokenizer(model):
    """Return a tokenizer instance for the given model.

    The function tries to provide sensible defaults for several known
    models. If a specific tokenizer cannot be loaded, it falls back to
    ``cl100k_base`` from ``tiktoken`` so token counting can still
    proceed.
    """
    name = (model or "").lower()
    try:
        if "openai" in name:
            return tiktoken.get_encoding("o200k_base")
        if "deepseek" in name:
            return AutoTokenizer.from_pretrained(
                "deepseek-ai/DeepSeek-V3",
                trust_remote_code=True,
                use_fast=True,
            )
        if "jina" in name:
            return AutoTokenizer.from_pretrained("xlm-roberta-base", use_fast=True)

    except Exception as e:  # pragma: no cover - defensive
        logging.error(f"获取tokenizer失败: {e}，使用cl100k_base Tokenizer")
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text, tokenizer):
    """Return the token count for the given text.

    Parameters
    ----------
    text: str
        Text to tokenize.
    tokenizer: the tokenizer
        a tokenizer instance.

    Args:
        tokenizer:
    """
    if not text:
        return 0

    try:
        if hasattr(tokenizer, "encode"):
            tokens = tokenizer.encode(text)
        else:  # pragma: no cover - should not happen
            tokens = tokenizer.tokenize(text)

        return len(tokens)
    except Exception as e:
        logging.error(f"计算Token失败: {str(e)}，使用估算")
        return int(len(text.split()) * 1.3)
