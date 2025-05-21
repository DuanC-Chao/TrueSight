#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
信息库管理器模块

本模块负责管理信息库，包括创建、查询、更新和删除信息库，以及信息库配置管理。
"""

import os
import json
import logging
import shutil
from datetime import datetime

# 导入工具模块
from backend.src.utils import file_utils

# 全局配置
config = {}
# 信息库列表
repositories = {}

def init(app_config):
    """
    初始化信息库管理器
    
    Args:
        app_config: 应用配置
    """
    global config
    
    # 合并应用配置
    if 'repository' in app_config:
        config.update(app_config['repository'])
    
    # 加载现有信息库
    _load_repositories()
    
    logging.info("信息库管理器初始化完成")

def _load_repositories():
    """加载现有信息库"""
    global repositories
    
    # 获取信息库根目录
    repository_root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                  'data', 'crawled_data')
    
    # 创建目录（如果不存在）
    os.makedirs(repository_root, exist_ok=True)
    
    # 遍历目录
    for name in os.listdir(repository_root):
        repo_dir = os.path.join(repository_root, name)
        if os.path.isdir(repo_dir):
            # 加载信息库配置
            config_file = os.path.join(repo_dir, 'repository_config.json')
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    repo_config = json.load(f)
                repo_config.setdefault('token_count_jina', 0)
                repo_config.setdefault('token_count_gpt4o', 0)
                repo_config.setdefault('token_count_deepseek', 0)
            else:
                # 创建默认配置
                repo_config = {
                    'name': name,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat(),
                    'source': 'unknown',
                    'auto_update': False,
                    'update_frequency': None,
                    'direct_import': False,
                    'embedding_model': 'jina-embeddings-v3',
                    'chunk_method': 'naive',
                    'parser_config': {
                        'chunk_token_num': 128,
                        'delimiter': '\\n!?;。；！？',
                        'html4excel': False,
                        'layout_recognize': True,
                        'raptor': {
                            'use_raptor': False
                        }
                    },
                    'file_type_mapping': {
                        '.txt': {
                            'chunk_method': 'naive',
                            'parser_config': {
                                'chunk_token_num': 128,
                                'delimiter': '\\n!?;。；！？',
                                'html4excel': False,
                                'layout_recognize': True,
                                'raptor': {
                                    'use_raptor': False
                                }
                            }
                        },
                        '.pdf': {
                            'chunk_method': 'naive',
                            'parser_config': {
                                'chunk_token_num': 128,
                                'delimiter': '\\n!?;。；！？',
                                'html4excel': False,
                                'layout_recognize': True,
                                'raptor': {
                                    'use_raptor': False
                                }
                            }
                        },
                        '.html': {
                            'chunk_method': 'naive',
                            'parser_config': {
                                'chunk_token_num': 128,
                                'delimiter': '\\n!?;。；！？',
                                'html4excel': False,
                                'layout_recognize': True,
                                'raptor': {
                                    'use_raptor': False
                                }
                            }
                        }
                    },
                    'dataset_id': None,
                    'status': 'incomplete',
                    'token_count_jina': 0,
                    'token_count_gpt4o': 0,
                    'token_count_deepseek': 0
                }
                
                # 保存配置
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(repo_config, f, ensure_ascii=False, indent=2)
            
            # 添加到信息库列表
            repositories[name] = repo_config

def create_repository(name, source='crawler', urls=None, config_override=None):
    """
    创建信息库
    
    Args:
        name: 信息库名称
        source: 信息库来源（crawler/upload）
        urls: 爬取URL列表（仅当source为crawler时有效）
        config_override: 配置覆盖
        
    Returns:
        repository: 信息库配置
    """
    global repositories
    
    # 检查信息库是否已存在
    if name in repositories:
        raise ValueError(f"信息库已存在: {name}")
    
    # 获取信息库目录
    repository_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                 'data', 'crawled_data', name)
    
    # 创建目录
    os.makedirs(repository_dir, exist_ok=True)
    
    # 创建默认配置
    repository_config = {
        'name': name,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'source': source,
        'auto_update': False,
        'update_frequency': None,
        'direct_import': False,
        'embedding_model': 'jina-embeddings-v3',
        'chunk_method': 'naive',
        'parser_config': {
            'chunk_token_num': 128,
            'delimiter': '\\n!?;。；！？',
            'html4excel': False,
            'layout_recognize': True,
            'raptor': {
                'use_raptor': False
            }
        },
        'file_type_mapping': {
            '.txt': {
                'chunk_method': 'naive',
                'parser_config': {
                    'chunk_token_num': 128,
                    'delimiter': '\\n!?;。；！？',
                    'html4excel': False,
                    'layout_recognize': True,
                    'raptor': {
                        'use_raptor': False
                    }
                }
            },
            '.pdf': {
                'chunk_method': 'naive',
                'parser_config': {
                    'chunk_token_num': 128,
                    'delimiter': '\\n!?;。；！？',
                    'html4excel': False,
                    'layout_recognize': True,
                    'raptor': {
                        'use_raptor': False
                    }
                }
            },
            '.html': {
                'chunk_method': 'naive',
                'parser_config': {
                    'chunk_token_num': 128,
                    'delimiter': '\\n!?;。；！？',
                    'html4excel': False,
                    'layout_recognize': True,
                    'raptor': {
                        'use_raptor': False
                    }
                }
            }
        },
        'dataset_id': None,
        'status': 'incomplete',
        'token_count_jina': 0,
        'token_count_gpt4o': 0,
        'token_count_deepseek': 0
    }
    
    # 如果是爬虫来源，记录URL
    if source == 'crawler' and urls:
        repository_config['urls'] = urls
    
    # 应用配置覆盖
    if config_override:
        repository_config.update(config_override)
    
    # 保存配置
    config_file = os.path.join(repository_dir, 'repository_config.json')
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(repository_config, f, ensure_ascii=False, indent=2)
    
    # 添加到信息库列表
    repositories[name] = repository_config
    
    logging.info(f"创建信息库: {name}, 来源: {source}")
    
    return repository_config

def get_repository(name):
    """
    获取信息库
    
    Args:
        name: 信息库名称
        
    Returns:
        repository: 信息库配置
    """
    if name in repositories:
        return repositories[name]
    else:
        return None

def get_all_repositories():
    """
    获取所有信息库
    
    Returns:
        repositories: 信息库列表
    """
    return list(repositories.values())

def update_repository(name, updates):
    """
    更新信息库
    
    Args:
        name: 信息库名称
        updates: 更新内容
        
    Returns:
        repository: 更新后的信息库配置
    """
    if name not in repositories:
        raise ValueError(f"信息库不存在: {name}")
    
    # 获取信息库配置
    repository = repositories[name]
    
    # 应用更新
    for key, value in updates.items():
        if key != 'name':  # 不允许修改名称
            repository[key] = value
    
    # 更新时间
    repository['updated_at'] = datetime.now().isoformat()
    
    # 保存配置
    repository_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                 'data', 'crawled_data', name)
    config_file = os.path.join(repository_dir, 'repository_config.json')
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(repository, f, ensure_ascii=False, indent=2)
    
    logging.info(f"更新信息库: {name}")
    
    return repository

def delete_repository(name):
    """
    删除信息库
    
    Args:
        name: 信息库名称
        
    Returns:
        success: 是否成功
    """
    if name not in repositories:
        raise ValueError(f"信息库不存在: {name}")
    
    # 获取信息库目录
    repository_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                 'data', 'crawled_data', name)
    
    # 删除目录
    shutil.rmtree(repository_dir)
    
    # 从列表中移除
    del repositories[name]
    
    logging.info(f"删除信息库: {name}")
    
    return True

def get_repository_files(name, file_types=None, include_summarized=True, include_qa=True):
    """
    获取信息库文件列表
    
    Args:
        name: 信息库名称
        file_types: 文件类型列表
        include_summarized: 是否包含总结文件
        include_qa: 是否包含问答文件
        
    Returns:
        files: 文件列表
    """
    if name not in repositories:
        raise ValueError(f"信息库不存在: {name}")
    
    # 获取信息库目录
    repository_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                 'data', 'crawled_data', name)
    
    # 设置文件类型
    if file_types is None:
        file_types = ['.txt', '.pdf', '.html']
    
    # 获取文件列表
    files = []
    for file_name in os.listdir(repository_dir):
        file_path = os.path.join(repository_dir, file_name)
        if os.path.isfile(file_path):
            # 检查文件类型
            _, ext = os.path.splitext(file_name)
            if ext.lower() in file_types:
                # 检查是否是总结文件或问答文件
                if (not include_summarized and '_summarized' in file_name) or \
                   (not include_qa and '_qa_' in file_name):
                    continue
                
                # 获取文件信息
                modified_time = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                file_info = {
                    'name': file_name,
                    'path': file_path,
                    'size': os.path.getsize(file_path),
                    'modified': modified_time,
                    'modified_time': modified_time,
                    'type': ext.lower()[1:]  # 去掉点号
                }
                
                files.append(file_info)
    
    return files

def get_repository_summary_files(name):
    """
    获取信息库总结文件列表
    
    Args:
        name: 信息库名称
        
    Returns:
        files: 文件列表
    """
    if name not in repositories:
        raise ValueError(f"信息库不存在: {name}")
    
    from backend.src.utils.config_loader import get_config

    cfg = get_config().get('processor', {})
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'data', cfg.get('summary_output_dir', 'summarizer_output'), name
    )

    files = []
    for file_name in os.listdir(repository_dir):
        if '_summarized.txt' in file_name:
            file_path = os.path.join(repository_dir, file_name)
            if os.path.isfile(file_path):
                modified_time = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                # 获取文件信息
                file_info = {
                    'name': file_name,
                    'path': file_path,
                    'size': os.path.getsize(file_path),
                    'modified': modified_time,
                    'modified_time': modified_time,
                    'type': 'txt'
                }
                
                files.append(file_info)
  
    return files

def get_repository_qa_files(name):
    """
    获取信息库问答文件列表
    
    Args:
        name: 信息库名称
        
    Returns:
        files: 文件列表
    """
    if name not in repositories:
        raise ValueError(f"信息库不存在: {name}")
    
    from backend.src.utils.config_loader import get_config

    cfg = get_config().get('processor', {})
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'data', cfg.get('qa_output_dir', 'qa_generator_output'), name
    )

    files = []
    for file_name in os.listdir(repository_dir):
        if '_qa_csv.csv' in file_name or '_qa_json.json' in file_name:
            file_path = os.path.join(repository_dir, file_name)
            if os.path.isfile(file_path):
                # 获取文件信息
                _, ext = os.path.splitext(file_name)
                modified_time = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                file_info = {
                    'name': file_name,
                    'path': file_path,
                    'size': os.path.getsize(file_path),
                    'modified': modified_time,
                    'modified_time': modified_time,
                    'type': ext.lower()[1:]  # 去掉点号
                }
                
                files.append(file_info)
   
    return files

def update_repository_status(name, status):
    """
    更新信息库状态
    
    Args:
        name: 信息库名称
        status: 状态（incomplete/complete/error）
        
    Returns:
        repository: 更新后的信息库配置
    """
    if name not in repositories:
        raise ValueError(f"信息库不存在: {name}")
    
    # 获取信息库配置
    repository = repositories[name]
    
    # 更新状态
    repository['status'] = status
    
    # 更新时间
    repository['updated_at'] = datetime.now().isoformat()
    
    # 保存配置
    repository_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                 'data', 'crawled_data', name)
    config_file = os.path.join(repository_dir, 'repository_config.json')
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(repository, f, ensure_ascii=False, indent=2)
    
    logging.info(f"更新信息库状态: {name} -> {status}")
    
    return repository

def set_repository_dataset_id(name, dataset_id):
    """
    设置信息库的Dataset ID
    
    Args:
        name: 信息库名称
        dataset_id: RAGFlow Dataset ID
        
    Returns:
        repository: 更新后的信息库配置
    """
    if name not in repositories:
        raise ValueError(f"信息库不存在: {name}")
    
    # 获取信息库配置
    repository = repositories[name]
    
    # 更新Dataset ID
    repository['dataset_id'] = dataset_id
    
    # 更新时间
    repository['updated_at'] = datetime.now().isoformat()
    
    # 保存配置
    repository_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                 'data', 'crawled_data', name)
    config_file = os.path.join(repository_dir, 'repository_config.json')
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(repository, f, ensure_ascii=False, indent=2)
    
    logging.info(f"设置信息库Dataset ID: {name} -> {dataset_id}")
    
    return repository

def set_auto_update(name, auto_update, update_frequency=None):
    """
    设置信息库自动更新
    
    Args:
        name: 信息库名称
        auto_update: 是否自动更新
        update_frequency: 更新频率（daily/weekly/monthly/yearly）
        
    Returns:
        repository: 更新后的信息库配置
    """
    if name not in repositories:
        raise ValueError(f"信息库不存在: {name}")
    
    # 获取信息库配置
    repository = repositories[name]
    
    # 检查是否是爬虫来源
    if repository['source'] != 'crawler' and auto_update:
        raise ValueError(f"只有爬虫来源的信息库才能设置自动更新")
    
    # 更新自动更新设置
    repository['auto_update'] = auto_update
    repository['update_frequency'] = update_frequency if auto_update else None
    
    # 更新时间
    repository['updated_at'] = datetime.now().isoformat()
    
    # 保存配置
    repository_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                 'data', 'crawled_data', name)
    config_file = os.path.join(repository_dir, 'repository_config.json')
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(repository, f, ensure_ascii=False, indent=2)
    
    logging.info(f"设置信息库自动更新: {name} -> {auto_update}, 频率: {update_frequency}")
    
    return repository

def set_direct_import(name, direct_import):
    """
    设置信息库直接入库
    
    Args:
        name: 信息库名称
        direct_import: 是否直接入库
        
    Returns:
        repository: 更新后的信息库配置
    """
    if name not in repositories:
        raise ValueError(f"信息库不存在: {name}")
    
    # 获取信息库配置
    repository = repositories[name]
    
    # 更新直接入库设置
    repository['direct_import'] = direct_import
    
    # 更新时间
    repository['updated_at'] = datetime.now().isoformat()
    
    # 保存配置
    repository_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                 'data', 'crawled_data', name)
    config_file = os.path.join(repository_dir, 'repository_config.json')
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(repository, f, ensure_ascii=False, indent=2)
    
    logging.info(f"设置信息库直接入库: {name} -> {direct_import}")
    
    return repository

def batch_update_repositories(repository_names, updates):
    """
    批量更新信息库
    
    Args:
        repository_names: 信息库名称列表
        updates: 更新内容
        
    Returns:
        results: 更新结果
    """
    results = {}
    
    for name in repository_names:
        try:
            if name in repositories:
                repository = update_repository(name, updates)
                results[name] = {
                    'success': True,
                    'repository': repository
                }
            else:
                results[name] = {
                    'success': False,
                    'error': f"信息库不存在: {name}"
                }
        except Exception as e:
            results[name] = {
                'success': False,
                'error': str(e)
            }
    
    return results

def batch_set_auto_update(repository_names, auto_update, update_frequency=None):
    """
    批量设置信息库自动更新
    
    Args:
        repository_names: 信息库名称列表
        auto_update: 是否自动更新
        update_frequency: 更新频率（daily/weekly/monthly/yearly）
        
    Returns:
        results: 更新结果
    """
    results = {}
    
    for name in repository_names:
        try:
            if name in repositories:
                # 检查是否是爬虫来源
                if repositories[name]['source'] != 'crawler' and auto_update:
                    results[name] = {
                        'success': False,
                        'error': f"只有爬虫来源的信息库才能设置自动更新"
                    }
                    continue
                
                repository = set_auto_update(name, auto_update, update_frequency)
                results[name] = {
                    'success': True,
                    'repository': repository
                }
            else:
                results[name] = {
                    'success': False,
                    'error': f"信息库不存在: {name}"
                }
        except Exception as e:
            results[name] = {
                'success': False,
                'error': str(e)
            }
    
    return results

def batch_set_direct_import(repository_names, direct_import):
    """
    批量设置信息库直接入库
    
    Args:
        repository_names: 信息库名称列表
        direct_import: 是否直接入库
        
    Returns:
        results: 更新结果
    """
    results = {}
    
    for name in repository_names:
        try:
            if name in repositories:
                repository = set_direct_import(name, direct_import)
                results[name] = {
                    'success': True,
                    'repository': repository
                }
            else:
                results[name] = {
                    'success': False,
                    'error': f"信息库不存在: {name}"
                }
        except Exception as e:
            results[name] = {
                'success': False,
                'error': str(e)
            }
    
    return results
