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
import copy
from datetime import datetime

# 导入工具模块
from ..utils import file_utils

# 全局配置
config = {}
# 信息库列表
repositories = {}

# 默认配置
DEFAULT_CONFIG = {
    'crawler': {
        'max_depth': 3,
        'max_threads': 5,
        'timeout': 30,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    },
    'processor': {
        'chunk_size': 1000,
        'overlap': 100
    }
}

# 默认的文件类型到 chunk method 映射
DEFAULT_FILE_TYPE_CHUNK_MAPPING = {
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
            'chunk_token_num': 256,
            'delimiter': '\\n!?;。；！？',
            'html4excel': False,
            'layout_recognize': True,
            'task_page_size': 12,
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
    },
    '.csv': {
        'chunk_method': 'qa',
        'parser_config': {
            'raptor': {
                'use_raptor': False
            }
        }
    },
    '.jpg': {
        'chunk_method': 'picture',
        'parser_config': {}
    },
    '.jpeg': {
        'chunk_method': 'picture',
        'parser_config': {}
    },
    '.png': {
        'chunk_method': 'picture',
        'parser_config': {}
    }
}

# 默认的Prompt配置
DEFAULT_PROMPT_CONFIG = {
    'summary_prompt': "请对以下内容进行总结，突出关键信息：",
    'summary_system_prompt': "你是一个专业的文档总结助手，擅长提取文本中的关键信息并生成简洁明了的总结。",
    'qa_stages': {
        'chunk': {
            'chunk_size': 1000,
            'chunk_overlap': 100,
            'prompt': "请根据以下内容生成5-10个高质量的问答对。\n要求：\n1. 问题应该清晰、具体、有价值\n2. 答案应该准确、完整、基于给定内容\n3. 避免过于简单或重复的问题\n4. 输出格式为JSON数组，每个元素包含\"q\"（问题）和\"a\"（答案）字段\n\n内容：",
            'system_prompt': "你是一个专业的问答对生成助手，擅长从文本中提取关键信息并生成有价值的问答对。"
        },
        'reduce': {
            'prompt': "请对以下问答对进行去重和筛选，保留最有价值、最独特的问答对。\n要求：\n1. 去除重复或高度相似的问题\n2. 保留信息量大、有深度的问答对\n3. 确保问题和答案的准确性\n4. 输出格式与输入相同的JSON数组\n\n问答对列表：",
            'system_prompt': "你是一个专业的内容审核助手，擅长识别重复或低质量的问答对，并保留最有价值的内容。"
        },
        'evaluate': {
            'prompt': "请对以下问答对进行质量评估。\n要求：\n1. 为每个问答对添加\"self_eval\"字段，评分范围1-5分\n2. 5分：问题清晰具体，答案准确完整，信息价值高\n3. 4分：问题较好，答案基本准确，有一定价值\n4. 3分：问题和答案一般，基本可用\n5. 2分：问题或答案有明显问题，价值较低\n6. 1分：问题不清楚或答案错误，应该删除\n7. 输出格式为JSON数组，保留原有的q和a字段，添加self_eval字段\n\n问答对列表：",
            'system_prompt': "你是一个专业的内容评估助手，擅长评估问答对的质量和价值。"
        }
    }
}

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
                    'file_type_chunk_mapping': copy.deepcopy(DEFAULT_FILE_TYPE_CHUNK_MAPPING),
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
        'file_type_chunk_mapping': copy.deepcopy(DEFAULT_FILE_TYPE_CHUNK_MAPPING),
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

    # 获取信息库配置
    repository = repositories[name]
    
    # 如果有关联的RAGFlow Dataset，尝试删除
    if repository.get('dataset_id'):
        try:
            from ..ragflow import ragflow_manager
            ragflow_manager.delete_dataset(repository['dataset_id'])
            logging.info(f"已删除RAGFlow Dataset: {repository['dataset_id']}")
        except Exception as e:
            logging.warning(f"删除RAGFlow Dataset失败: {str(e)}，将继续删除本地信息库")

    # 获取基础数据目录
    base_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data')
    
    # 需要删除的目录列表
    directories_to_delete = [
        os.path.join(base_data_dir, 'crawled_data', name),
        os.path.join(base_data_dir, 'summarizer_output', name),
        # 新的QA输出目录结构
        os.path.join(base_data_dir, 'qa_generator_output', 'json_output', f"{name}_json_qa"),
        os.path.join(base_data_dir, 'qa_generator_output', 'csv_output', f"{name}_csv_qa"),
        os.path.join(base_data_dir, 'qa_generator_output', 'cost_output')  # 可能包含相关的成本文件
    ]
    
    # 删除所有相关目录
    for directory in directories_to_delete:
        if os.path.exists(directory):
            try:
                if directory.endswith('cost_output'):
                    # 对于cost_output目录，只删除相关的成本文件
                    cost_file = os.path.join(directory, f"{name}_cost.txt")
                    if os.path.exists(cost_file):
                        os.remove(cost_file)
                        logging.info(f"删除成本文件: {cost_file}")
                else:
                    # 其他目录直接删除
                    shutil.rmtree(directory)
                    logging.info(f"删除目录: {directory}")
            except Exception as e:
                logging.error(f"删除目录失败: {directory}, 错误: {str(e)}")

    # 从任务管理器中清理相关任务（如果有的话）
    try:
        from ..utils.task_manager import task_manager
        # 获取该仓库的所有任务
        tasks = task_manager.get_repository_tasks(name)
        for task in tasks:
            # 取消运行中的任务
            if task['status'] in ['pending', 'running']:
                task_manager.cancel_task(task['id'])
                logging.info(f"取消任务: {task['id']}")
    except Exception as e:
        logging.error(f"清理任务失败: {str(e)}")

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

    # 获取信息库目录
    repository_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                 'data', 'crawled_data', name)
    summary_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                               'data', 'summarizer_output', name)

    # 需要过滤的文件名模式
    filtered_files = {
        'all_summaries.txt',
        'content_hashes.json'
    }
    
    # 需要过滤的文件名前缀
    filtered_prefixes = [
        'token_count_deepseek_',
        'token_count_gpt4o_',
        'token_count_jina_'
    ]

    files = []
    search_dirs = [repository_dir, summary_dir]
    for directory in search_dirs:
        if not os.path.isdir(directory):
            continue
        for file_name in os.listdir(directory):
            # 检查是否是总结文件
            if '_summarized.txt' in file_name or file_name.endswith('_summary.txt'):
                # 检查是否需要过滤
                should_filter = False
                
                # 检查是否在过滤列表中
                if file_name in filtered_files:
                    should_filter = True
                
                # 检查是否以过滤前缀开头
                for prefix in filtered_prefixes:
                    if file_name.startswith(prefix):
                        should_filter = True
                        break
                
                # 如果不需要过滤，添加到结果中
                if not should_filter:
                    file_path = os.path.join(directory, file_name)
                    if os.path.isfile(file_path):
                        modified_time = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
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

    # 基础数据目录
    base_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data')
    
    # QA文件可能存在的目录
    qa_csv_dir = os.path.join(base_data_dir, 'qa_generator_output', 'csv_output', f"{name}_csv_qa")
    qa_json_dir = os.path.join(base_data_dir, 'qa_generator_output', 'json_output', f"{name}_json_qa")
    
    files = []
    
    # 首先检查CSV目录（这是主要的输出格式，优先使用）
    csv_files_found = False
    if os.path.isdir(qa_csv_dir):
        for file_name in os.listdir(qa_csv_dir):
            if file_name.endswith('.csv'):
                file_path = os.path.join(qa_csv_dir, file_name)
                if os.path.isfile(file_path):
                    modified_time = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                    file_info = {
                        'name': file_name,
                        'path': file_path,
                        'size': os.path.getsize(file_path),
                        'modified': modified_time,
                        'modified_time': modified_time,
                        'type': 'csv'
                    }
                    files.append(file_info)
                    csv_files_found = True
    
    # 只有在没有找到CSV文件时，才检查JSON目录（作为备份/中间格式）
    if not csv_files_found and os.path.isdir(qa_json_dir):
        for file_name in os.listdir(qa_json_dir):
            if file_name.endswith('.json') and file_name != 'content_hashes.json':
                file_path = os.path.join(qa_json_dir, file_name)
                if os.path.isfile(file_path):
                    modified_time = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                    file_info = {
                        'name': file_name,
                        'path': file_path,
                        'size': os.path.getsize(file_path),
                        'modified': modified_time,
                        'modified_time': modified_time,
                        'type': 'json'
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

def update_file_type_chunk_mapping(name, file_type, chunk_method, parser_config=None):
    """
    更新信息库的文件类型到 chunk method 映射

    Args:
        name: 信息库名称
        file_type: 文件类型（如 .txt, .pdf）
        chunk_method: chunk 方法
        parser_config: 解析器配置

    Returns:
        repository: 更新后的信息库配置
    """
    if name not in repositories:
        raise ValueError(f"信息库不存在: {name}")

    # 获取信息库配置
    repository = repositories[name]

    # 确保有 file_type_chunk_mapping
    if 'file_type_chunk_mapping' not in repository:
        repository['file_type_chunk_mapping'] = copy.deepcopy(DEFAULT_FILE_TYPE_CHUNK_MAPPING)

    # 更新映射
    if file_type not in repository['file_type_chunk_mapping']:
        repository['file_type_chunk_mapping'][file_type] = {}
    
    repository['file_type_chunk_mapping'][file_type]['chunk_method'] = chunk_method
    
    if parser_config:
        repository['file_type_chunk_mapping'][file_type]['parser_config'] = parser_config

    # 更新时间
    repository['updated_at'] = datetime.now().isoformat()

    # 保存配置
    repository_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                 'data', 'crawled_data', name)
    config_file = os.path.join(repository_dir, 'repository_config.json')
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(repository, f, ensure_ascii=False, indent=2)

    logging.info(f"更新文件类型映射: {name} -> {file_type}: {chunk_method}")

    return repository

def get_file_type_chunk_mapping(name):
    """
    获取信息库的文件类型到 chunk method 映射

    Args:
        name: 信息库名称

    Returns:
        mapping: 文件类型映射
    """
    if name not in repositories:
        raise ValueError(f"信息库不存在: {name}")

    repository = repositories[name]
    
    # 确保有 file_type_chunk_mapping
    if 'file_type_chunk_mapping' not in repository:
        return copy.deepcopy(DEFAULT_FILE_TYPE_CHUNK_MAPPING)
    
    return repository['file_type_chunk_mapping']

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

def get_repository_prompt_config(name):
    """
    获取信息库的Prompt配置

    Args:
        name: 信息库名称

    Returns:
        prompt_config: Prompt配置
    """
    if name not in repositories:
        raise ValueError(f"信息库不存在: {name}")

    repository = repositories[name]
    
    # 如果信息库没有自定义Prompt配置，返回默认配置
    if 'prompt_config' not in repository:
        return copy.deepcopy(DEFAULT_PROMPT_CONFIG)
    
    return repository['prompt_config']

def update_repository_prompt_config(name, prompt_config):
    """
    更新信息库的Prompt配置

    Args:
        name: 信息库名称
        prompt_config: Prompt配置

    Returns:
        repository: 更新后的信息库配置
    """
    if name not in repositories:
        raise ValueError(f"信息库不存在: {name}")

    # 获取信息库配置
    repository = repositories[name]

    # 更新Prompt配置
    repository['prompt_config'] = prompt_config

    # 更新时间
    repository['updated_at'] = datetime.now().isoformat()

    # 保存配置
    repository_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                 'data', 'crawled_data', name)
    config_file = os.path.join(repository_dir, 'repository_config.json')
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(repository, f, ensure_ascii=False, indent=2)

    logging.info(f"更新信息库Prompt配置: {name}")

    return repository

def reset_repository_prompt_config(name):
    """
    重置信息库的Prompt配置为默认值

    Args:
        name: 信息库名称

    Returns:
        repository: 更新后的信息库配置
    """
    if name not in repositories:
        raise ValueError(f"信息库不存在: {name}")

    # 获取信息库配置
    repository = repositories[name]

    # 重置为默认配置
    repository['prompt_config'] = copy.deepcopy(DEFAULT_PROMPT_CONFIG)

    # 更新时间
    repository['updated_at'] = datetime.now().isoformat()

    # 保存配置
    repository_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                 'data', 'crawled_data', name)
    config_file = os.path.join(repository_dir, 'repository_config.json')
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(repository, f, ensure_ascii=False, indent=2)

    logging.info(f"重置信息库Prompt配置: {name}")

    return repository

def get_merged_prompt_config(name, global_config=None):
    """
    获取合并后的Prompt配置（信息库配置覆盖全局配置）

    Args:
        name: 信息库名称
        global_config: 全局配置（可选）

    Returns:
        merged_config: 合并后的配置
    """
    if name not in repositories:
        raise ValueError(f"信息库不存在: {name}")

    # 获取全局配置
    if global_config is None:
        # 从配置管理器获取全局配置
        try:
            from ..config import config_manager
            global_config = config_manager.get_config()
        except:
            global_config = {}

    # 获取全局Prompt配置
    global_prompt_config = global_config.get('processor', {})
    
    # 构建全局Prompt配置结构
    global_prompts = {
        'summary_prompt': global_prompt_config.get('summary_prompt', DEFAULT_PROMPT_CONFIG['summary_prompt']),
        'summary_system_prompt': global_prompt_config.get('summary_system_prompt', DEFAULT_PROMPT_CONFIG['summary_system_prompt']),
        'qa_stages': global_prompt_config.get('qa_stages', DEFAULT_PROMPT_CONFIG['qa_stages'])
    }

    # 获取信息库Prompt配置
    repository = repositories[name]
    repo_prompt_config = repository.get('prompt_config', {})

    # 合并配置（信息库配置覆盖全局配置）
    merged_config = copy.deepcopy(global_prompts)
    
    # 递归合并配置
    def merge_dict(base, override):
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                merge_dict(base[key], value)
            else:
                base[key] = value
    
    merge_dict(merged_config, repo_prompt_config)
    
    return merged_config
