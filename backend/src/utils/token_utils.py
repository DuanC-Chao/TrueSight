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
    """Return a tokenizer instance for the given model name.

    The function falls back to ``cl100k_base`` encoding if a specialised
    tokenizer cannot be loaded. HuggingFace models are loaded lazily and
    any failures will be logged and ignored.
    """
    if not model:
        model = "gpt-3.5-turbo"

    name = model.lower()

    try:
        if name.startswith("gpt-4") or name.startswith("gpt-3.5"):
            # All current OpenAI ChatGPT models use cl100k_base
            return tiktoken.get_encoding("cl100k_base")
        if "deepseek" in name:
            try:
                return AutoTokenizer.from_pretrained(
                    "deepseek-ai/deepseek-llm-7b-base",
                    trust_remote_code=True,
                    use_fast=True,
                )
            except Exception as e:  # pragma: no cover - network in tests
                logging.error(f"加载 DeepSeek tokenizer 失败: {e}")
                return tiktoken.get_encoding("cl100k_base")
        if "jina" in name:
            try:
                return AutoTokenizer.from_pretrained(
                    "xlm-roberta-base",
                    use_fast=True,
                )
            except Exception as e:  # pragma: no cover - network in tests
                logging.error(f"加载 Jina tokenizer 失败: {e}")
                return tiktoken.get_encoding("cl100k_base")
    except Exception as e:
        logging.error(f"获取 tokenizer 失败: {e}")

    return tiktoken.get_encoding("cl100k_base")

def count_tokens(text, tokenizer_or_model="gpt-3.5-turbo"):
    """Return the number of tokens in ``text``.

    ``tokenizer_or_model`` can be either a model name or a tokenizer/encoding
    instance returned by :func:`get_tokenizer`.
    """
    if not text:
        return 0

    # Determine tokenizer
    if isinstance(tokenizer_or_model, str):
        tokenizer = get_tokenizer(tokenizer_or_model)
    else:
        tokenizer = tokenizer_or_model

    try:
        tokens = tokenizer.encode(text)
        return len(tokens)
    except Exception as e:  # pragma: no cover - fallback
        logging.error(f"计算Token失败: {e}")
        return int(len(text.split()) * 1.3)
