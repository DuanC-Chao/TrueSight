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
def get_tokenizer(model: str):
    """Return a tokenizer instance for the given model name."""
    model_l = model.lower()

    if model_l in {"gpt-4o", "gpt4o"}:
        return tiktoken.encoding_for_model("gpt-4o")
    if "deepseek" in model_l:
        return AutoTokenizer.from_pretrained(
            "deepseek-ai/deepseek-llm-7b-base",
            trust_remote_code=True,
            use_fast=True,
        )
    if "jina" in model_l or "xlm-roberta" in model_l:
        return AutoTokenizer.from_pretrained("xlm-roberta-base", use_fast=True)

    try:
        return tiktoken.encoding_for_model(model)
    except Exception:
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text, tokenizer_or_model="gpt-3.5-turbo"):
    """计算文本的Token数量."""
    if not text:
        return 0

    try:
        if hasattr(tokenizer_or_model, "encode"):
            tokenizer = tokenizer_or_model
        else:
            tokenizer = get_tokenizer(str(tokenizer_or_model))

        tokens = tokenizer.encode(text)
        return len(tokens)
    except Exception as e:
        logging.error(f"计算Token失败: {str(e)}")
        return int(len(text.split()) * 1.3)
