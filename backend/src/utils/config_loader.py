#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置加载器模块

本模块负责加载和管理应用配置。
"""

import os
import yaml
import json
import logging

# 全局配置缓存
_config_cache = None


def get_config(config_path=None):
    """
    获取全局配置

    如果配置已缓存，则返回缓存的配置，否则加载配置

    Args:
        config_path: 配置文件路径，如果为None则使用默认路径

    Returns:
        config: 配置字典
    """
    global _config_cache

    # 如果配置已缓存，则返回缓存的配置
    if _config_cache is not None:
        return _config_cache

    # 加载配置
    _config_cache = load_config(config_path)
    return _config_cache


def load_config(config_path=None):
    """
    加载配置文件

    Args:
        config_path: 配置文件路径，如果为None则使用默认路径

    Returns:
        config: 配置字典
    """
    if config_path is None:
        # 使用默认配置文件路径
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'config', 'config.yaml')

    # 检查配置文件是否存在
    if not os.path.exists(config_path):
        logging.warning(f"配置文件不存在: {config_path}，将使用默认配置")
        return create_default_config(config_path)

    # 加载配置文件
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                config = yaml.safe_load(f)
            elif config_path.endswith('.json'):
                config = json.load(f)
            else:
                logging.error(f"不支持的配置文件格式: {config_path}")
                return create_default_config(config_path)

        logging.info(f"成功加载配置文件: {config_path}")
        return config

    except Exception as e:
        logging.error(f"加载配置文件失败: {config_path}, 错误: {str(e)}")
        return create_default_config(config_path)


def create_default_config(config_path=None):
    """
    创建默认配置

    Args:
        config_path: 配置文件路径，如果不为None则保存配置

    Returns:
        config: 默认配置字典
    """
    # 默认配置
    default_config = {
        'debug': False,
        'server': {
            'host': '0.0.0.0',
            'port': 5000
        },
        'log_level': 'INFO',
        'crawler': {
            'max_depth': 3,
            'max_threads': 10,
            'timeout': 30,
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        },
        'processor': {
            'llm_api_key': os.environ.get('LLM_API_KEY', ''),
            'llm_model': 'gpt-3.5-turbo'
        },
        'repository': {
            'default_embedding_model': 'jina-embeddings-v3',
            'default_chunk_method': 'naive'
        },
        'ragflow': {
            'base_url': os.environ.get('RAGFLOW_BASE_URL', 'http://192.168.0.130'),
            'api_key': os.environ.get('RAGFLOW_API_KEY', '')
        },
        'scheduler': {
            'check_interval': 60  # 秒
        }
    }

    # 如果指定了配置文件路径，则保存默认配置
    if config_path:
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(config_path), exist_ok=True)

            # 保存配置
            with open(config_path, 'w', encoding='utf-8') as f:
                if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                    yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
                elif config_path.endswith('.json'):
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
                else:
                    # 默认使用YAML格式
                    yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)

            logging.info(f"已创建默认配置文件: {config_path}")

        except Exception as e:
            logging.error(f"创建默认配置文件失败: {config_path}, 错误: {str(e)}")

    return default_config


def save_config(config, config_path=None):
    """
    保存配置

    Args:
        config: 配置字典
        config_path: 配置文件路径，如果为None则使用默认路径

    Returns:
        success: 是否成功
    """
    if config_path is None:
        # 使用默认配置文件路径
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'config', 'config.yaml')

    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        # 保存配置
        with open(config_path, 'w', encoding='utf-8') as f:
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            elif config_path.endswith('.json'):
                json.dump(config, f, ensure_ascii=False, indent=2)
            else:
                # 默认使用YAML格式
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

        logging.info(f"成功保存配置文件: {config_path}")

        # 更新配置缓存
        global _config_cache
        _config_cache = config

        return True

    except Exception as e:
        logging.error(f"保存配置文件失败: {config_path}, 错误: {str(e)}")
        return False


def update_config(updates, config_path=None):
    """
    更新配置

    Args:
        updates: 更新内容
        config_path: 配置文件路径，如果为None则使用默认路径

    Returns:
        success: 是否成功
    """
    # 加载现有配置
    config = get_config(config_path)

    # 递归更新配置
    def update_dict(d, u):
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                d[k] = update_dict(d[k], v)
            else:
                d[k] = v
        return d

    # 应用更新
    config = update_dict(config, updates)

    # 保存配置
    success = save_config(config, config_path)

    return success
