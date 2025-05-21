#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
预处理管理器模块

本模块负责管理文档预处理任务，包括Token计算、内容总结和问答对生成。
"""

import os
import json
import logging
import hashlib
import time
import threading
import requests
from datetime import datetime

# 导入工具模块
from backend.src.utils import file_utils, token_utils
from backend.src.repository import repository_manager

# 全局配置
config = {}
# 预处理状态
process_status = {}
# 处理锁
process_lock = threading.Lock()

def init(app_config):
    """
    初始化预处理管理器
    
    Args:
        app_config: 应用配置
    """
    global config
    
    # 加载预处理配置
    processor_config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                        'config', 'processor.yaml')
    
    if os.path.exists(processor_config_path):
        import yaml
        with open(processor_config_path, 'r', encoding='utf-8') as f:
            processor_config = yaml.safe_load(f)
        config.update(processor_config)
    
    # 合并应用配置
    if 'processor' in app_config:
        config.update(app_config['processor'])
    
    logging.info("预处理管理器初始化完成")

def start_token_calculation(repository_name):
    """
    开始Token计算任务
    
    Args:
        repository_name: 信息库名称
        
    Returns:
        task_id: 任务ID
        token_count: 当前Token计数（初始为0）
    """
    # 生成任务ID
    task_id = f"token_{int(time.time())}"
    
    # 初始化任务状态
    process_status[task_id] = {
        'status': 'running',
        'repository_name': repository_name,
        'task_type': 'token_calculation',
        'start_time': datetime.now().isoformat(),
        'end_time': None,
        'total_files': 0,
        'processed_files': 0,
        'total_tokens': 0,
        'error': None
    }
    
    # 创建并启动处理线程
    process_thread = threading.Thread(
        target=_token_calculation_worker,
        args=(task_id, repository_name)
    )
    process_thread.daemon = True
    process_thread.start()
    
    logging.info(f"Token计算任务 {task_id} 已启动，信息库: {repository_name}")
    
    # 返回任务ID和初始Token计数
    return task_id, {
        'token_count_jina': 0,
        'token_count_gpt4o': 0,
        'token_count_deepseek': 0,
    }

def _token_calculation_worker(task_id, repository_name):
    """
    Token计算工作线程
    
    Args:
        task_id: 任务ID
        repository_name: 信息库名称
    """
    try:
        # 获取信息库目录
        repository_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                     'data', 'crawled_data', repository_name)
        
        # 检查目录是否存在
        if not os.path.exists(repository_dir):
            raise FileNotFoundError(f"信息库目录不存在: {repository_dir}")
        
        # 获取所有文本文件
        files = file_utils.list_files(repository_dir, ['.txt', '.pdf', '.html'])
        
        # 更新任务状态
        with process_lock:
            process_status[task_id]['total_files'] = len(files)
        
        # 为多种模型准备tokenizer
        tokenizers = {
            'token_count_gpt4o': token_utils.get_tokenizer('gpt-4o'),
            'token_count_deepseek': token_utils.get_tokenizer('deepseek'),
            'token_count_jina': token_utils.get_tokenizer('jina'),
        }

        token_counts = {k: 0 for k in tokenizers}

        # 创建Token跟踪文件
        token_tracker_paths = {
            k: os.path.join(repository_dir, f"{k}.txt") for k in tokenizers
        }
        
        # 处理每个文件
        processed_files = 0
        for file_path in files:
            try:
                content = file_utils.read_file(file_path)

                for key, tokenizer in tokenizers.items():
                    tokens = token_utils.count_tokens(content, tokenizer)
                    token_counts[key] += tokens
                    with open(token_tracker_paths[key], 'a', encoding='utf-8') as f:
                        f.write(f"{os.path.basename(file_path)}: {tokens}\n")

                processed_files += 1
                with process_lock:
                    process_status[task_id]['processed_files'] = processed_files
                    process_status[task_id]['total_tokens'] = sum(token_counts.values())

            except Exception as e:
                logging.error(f"处理文件失败: {file_path}, 错误: {str(e)}")

        for key, count in token_counts.items():
            with open(token_tracker_paths[key], 'a', encoding='utf-8') as f:
                f.write(f"\n总Token数: {count}\n")

        # 更新信息库的Token计数
        try:
            repository_manager.update_repository(repository_name, {
                **token_counts,
                'updated_at': datetime.now().isoformat()
            })
        except Exception as e:
            logging.error(f"更新信息库Token计数失败: {str(e)}")
        
        # 更新任务状态
        with process_lock:
            process_status[task_id]['status'] = 'completed'
            process_status[task_id]['end_time'] = datetime.now().isoformat()
        
        logging.info(
            f"Token计算任务 {task_id} 已完成，信息库: {repository_name}, 总Token数: {sum(token_counts.values())}"
        )
    
    except Exception as e:
        # 更新任务状态为失败
        with process_lock:
            process_status[task_id]['status'] = 'failed'
            process_status[task_id]['error'] = str(e)
            process_status[task_id]['end_time'] = datetime.now().isoformat()
        
        logging.error(f"Token计算任务 {task_id} 失败: {str(e)}")

def start_summary_generation(repository_name, llm_config=None):
    """
    开始内容总结任务
    
    Args:
        repository_name: 信息库名称
        llm_config: LLM配置（可选）
        
    Returns:
        task_id: 任务ID
    """
    # 生成任务ID
    task_id = f"summary_{int(time.time())}"
    
    # 初始化任务状态
    process_status[task_id] = {
        'status': 'running',
        'repository_name': repository_name,
        'task_type': 'summary_generation',
        'start_time': datetime.now().isoformat(),
        'end_time': None,
        'total_files': 0,
        'processed_files': 0,
        'error': None
    }
    
    # 创建并启动处理线程
    process_thread = threading.Thread(
        target=_summary_generation_worker,
        args=(task_id, repository_name, llm_config)
    )
    process_thread.daemon = True
    process_thread.start()
    
    logging.info(f"内容总结任务 {task_id} 已启动，信息库: {repository_name}")
    
    return task_id

def _summary_generation_worker(task_id, repository_name, llm_config=None):
    """
    内容总结工作线程
    
    Args:
        task_id: 任务ID
        repository_name: 信息库名称
        llm_config: LLM配置（可选）
    """
    try:
        # 获取信息库目录
        repository_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                     'data', 'crawled_data', repository_name)
        
        # 检查目录是否存在
        if not os.path.exists(repository_dir):
            raise FileNotFoundError(f"信息库目录不存在: {repository_dir}")
        
        # 创建输出目录
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                 'data', config.get('summary_output_dir', 'summarizer_output'), repository_name)
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取所有文本文件
        files = file_utils.list_files(repository_dir, ['.txt'])
        
        # 更新任务状态
        with process_lock:
            process_status[task_id]['total_files'] = len(files)
        
        # 处理每个文件
        processed_files = 0
        all_summaries = []
        
        # 获取内容哈希记录
        content_hashes_path = os.path.join(output_dir, 'content_hashes.json')
        content_hashes = {}
        if os.path.exists(content_hashes_path):
            try:
                with open(content_hashes_path, 'r', encoding='utf-8') as f:
                    content_hashes = json.load(f)
            except:
                content_hashes = {}
        
        # 处理每个文件
        for file_path in files:
            try:
                file_name = os.path.basename(file_path)
                
                # 读取文件内容
                content = file_utils.read_file(file_path)
                
                # 计算内容哈希
                content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
                
                # 检查是否需要处理
                if config.get('incremental_processing', True) and file_name in content_hashes and content_hashes[file_name] == content_hash:
                    # 文件内容未变，跳过处理
                    logging.info(f"文件内容未变，跳过处理: {file_name}")
                    
                    # 读取已有总结
                    summary_file = os.path.join(output_dir, f"{os.path.splitext(file_name)[0]}_summary.txt")
                    if os.path.exists(summary_file):
                        summary = file_utils.read_file(summary_file)
                        all_summaries.append(f"## {os.path.splitext(file_name)[0]}\n\n{summary}\n\n")
                    
                    # 更新处理进度
                    processed_files += 1
                    with process_lock:
                        process_status[task_id]['processed_files'] = processed_files
                    
                    continue
                
                # 生成总结
                summary = _generate_summary(content, llm_config)
                
                # 保存总结
                summary_file = os.path.join(output_dir, f"{os.path.splitext(file_name)[0]}_summary.txt")
                with open(summary_file, 'w', encoding='utf-8') as f:
                    f.write(summary)
                
                # 添加到总结集合
                all_summaries.append(f"## {os.path.splitext(file_name)[0]}\n\n{summary}\n\n")
                
                # 更新内容哈希
                content_hashes[file_name] = content_hash
                
                # 更新处理进度
                processed_files += 1
                with process_lock:
                    process_status[task_id]['processed_files'] = processed_files
            
            except Exception as e:
                logging.error(f"处理文件失败: {file_path}, 错误: {str(e)}")
        
        # 保存内容哈希记录
        with open(content_hashes_path, 'w', encoding='utf-8') as f:
            json.dump(content_hashes, f, indent=2)
        
        # 保存总结合集
        all_summaries_file = os.path.join(output_dir, 'all_summaries.txt')
        with open(all_summaries_file, 'w', encoding='utf-8') as f:
            f.write("# 信息库总结\n\n")
            f.write(f"信息库: {repository_name}\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            f.write("".join(all_summaries))
        
        # 更新信息库的更新时间
        try:
            repository_manager.update_repository(repository_name, {
                'updated_at': datetime.now().isoformat()
            })
        except Exception as e:
            logging.error(f"更新信息库更新时间失败: {str(e)}")
        
        # 更新任务状态
        with process_lock:
            process_status[task_id]['status'] = 'completed'
            process_status[task_id]['end_time'] = datetime.now().isoformat()
        
        logging.info(f"内容总结任务 {task_id} 已完成，信息库: {repository_name}")
    
    except Exception as e:
        # 更新任务状态为失败
        with process_lock:
            process_status[task_id]['status'] = 'failed'
            process_status[task_id]['error'] = str(e)
            process_status[task_id]['end_time'] = datetime.now().isoformat()
        
        logging.error(f"内容总结任务 {task_id} 失败: {str(e)}")

def _generate_summary(content, llm_config=None):
    """
    生成内容总结
    
    Args:
        content: 要总结的内容
        llm_config: LLM配置（可选）
        
    Returns:
        summary: 生成的总结
    """
    # 合并LLM配置
    merged_config = config.copy()
    if llm_config:
        merged_config.update(llm_config)
    
    # 获取LLM配置
    provider = merged_config.get('provider', 'openai')
    
    # 获取提供商特定配置
    provider_config = merged_config.get(provider, {})
    api_key = provider_config.get('api_key', merged_config.get('api_key', ''))
    model = provider_config.get('model', merged_config.get('model', 'gpt-3.5-turbo'))
    
    # 获取API基础URL
    api_base_urls = {
        'openai': 'https://api.openai.com/v1/chat/completions',
        'qwen': 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions',
        'deepseek': 'https://api.deepseek.com/v1/chat/completions'
    }
    api_base_url = api_base_urls.get(provider, api_base_urls['openai'])
    
    # 获取提示词
    summary_prompt = merged_config.get('summary_prompt', '请对以下内容进行总结，突出关键信息：')
    summary_system_prompt = merged_config.get('summary_system_prompt', '你是一个专业的文档总结助手，擅长提取文本中的关键信息并生成简洁明了的总结。')
    
    # 准备请求数据
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    # 特殊处理Qwen API
    if provider == 'qwen':
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'X-DashScope-SSE': 'disable'
        }
    
    data = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': summary_system_prompt},
            {'role': 'user', 'content': f"{summary_prompt}\n\n{content}"}
        ],
        'temperature': merged_config.get('temperature', 0.2),
        'max_tokens': merged_config.get('max_tokens', 2000)
    }
    
    # 发送请求
    response = requests.post(api_base_url, headers=headers, json=data)
    
    # 检查响应
    if response.status_code != 200:
        error_msg = f"API请求失败: {response.status_code} {response.text}"
        logging.error(error_msg)
        raise Exception(error_msg)
    
    # 解析响应
    response_data = response.json()
    
    # 提取总结
    if provider == 'openai' or provider == 'deepseek' or provider == 'qwen':
        summary = response_data['choices'][0]['message']['content']
    else:
        summary = response_data['choices'][0]['message']['content']
    
    return summary

def start_qa_generation(repository_name, llm_config=None):
    """
    开始问答对生成任务
    
    Args:
        repository_name: 信息库名称
        llm_config: LLM配置（可选）
        
    Returns:
        task_id: 任务ID
    """
    # 生成任务ID
    task_id = f"qa_{int(time.time())}"
    
    # 初始化任务状态
    process_status[task_id] = {
        'status': 'running',
        'repository_name': repository_name,
        'task_type': 'qa_generation',
        'start_time': datetime.now().isoformat(),
        'end_time': None,
        'total_files': 0,
        'processed_files': 0,
        'total_qa_pairs': 0,
        'error': None
    }
    
    # 创建并启动处理线程
    process_thread = threading.Thread(
        target=_qa_generation_worker,
        args=(task_id, repository_name, llm_config)
    )
    process_thread.daemon = True
    process_thread.start()
    
    logging.info(f"问答对生成任务 {task_id} 已启动，信息库: {repository_name}")
    
    return task_id

def _qa_generation_worker(task_id, repository_name, llm_config=None):
    """
    问答对生成工作线程
    
    Args:
        task_id: 任务ID
        repository_name: 信息库名称
        llm_config: LLM配置（可选）
    """
    try:
        # 获取信息库目录
        repository_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                     'data', 'crawled_data', repository_name)
        
        # 检查目录是否存在
        if not os.path.exists(repository_dir):
            raise FileNotFoundError(f"信息库目录不存在: {repository_dir}")
        
        # 创建输出目录
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                 'data', config.get('qa_output_dir', 'qa_generator_output'), repository_name)
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取所有文本文件
        files = file_utils.list_files(repository_dir, ['.txt'])
        
        # 更新任务状态
        with process_lock:
            process_status[task_id]['total_files'] = len(files)
        
        # 获取内容哈希记录
        content_hashes_path = os.path.join(output_dir, 'content_hashes.json')
        content_hashes = {}
        if os.path.exists(content_hashes_path):
            try:
                with open(content_hashes_path, 'r', encoding='utf-8') as f:
                    content_hashes = json.load(f)
            except:
                content_hashes = {}
        
        # 处理每个文件
        processed_files = 0
        all_qa_pairs = []
        
        for file_path in files:
            try:
                file_name = os.path.basename(file_path)
                
                # 检查是否在忽略列表中
                ignored_filenames = config.get('ignored_filenames', [])
                if file_name in ignored_filenames:
                    logging.info(f"文件在忽略列表中，跳过处理: {file_name}")
                    continue
                
                # 读取文件内容
                content = file_utils.read_file(file_path)
                
                # 计算内容哈希
                content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
                
                # 检查是否需要处理
                if config.get('incremental_processing', True) and file_name in content_hashes and content_hashes[file_name] == content_hash:
                    # 文件内容未变，跳过处理
                    logging.info(f"文件内容未变，跳过处理: {file_name}")
                    
                    # 读取已有问答对
                    qa_file = os.path.join(output_dir, f"{os.path.splitext(file_name)[0]}_qa.json")
                    if os.path.exists(qa_file):
                        with open(qa_file, 'r', encoding='utf-8') as f:
                            qa_pairs = json.load(f)
                        all_qa_pairs.extend(qa_pairs)
                    
                    # 更新处理进度
                    processed_files += 1
                    with process_lock:
                        process_status[task_id]['processed_files'] = processed_files
                    
                    continue
                
                # 生成问答对
                qa_pairs = _generate_qa_pairs(content, llm_config)
                
                # 保存问答对
                qa_file = os.path.join(output_dir, f"{os.path.splitext(file_name)[0]}_qa.json")
                with open(qa_file, 'w', encoding='utf-8') as f:
                    json.dump(qa_pairs, f, ensure_ascii=False, indent=2)
                
                # 添加到问答对集合
                all_qa_pairs.extend(qa_pairs)
                
                # 更新内容哈希
                content_hashes[file_name] = content_hash
                
                # 更新处理进度
                processed_files += 1
                with process_lock:
                    process_status[task_id]['processed_files'] = processed_files
                    process_status[task_id]['total_qa_pairs'] = len(all_qa_pairs)
            
            except Exception as e:
                logging.error(f"处理文件失败: {file_path}, 错误: {str(e)}")
        
        # 保存内容哈希记录
        with open(content_hashes_path, 'w', encoding='utf-8') as f:
            json.dump(content_hashes, f, indent=2)
        
        # 保存所有问答对
        all_qa_file = os.path.join(output_dir, 'all_qa.json')
        with open(all_qa_file, 'w', encoding='utf-8') as f:
            json.dump(all_qa_pairs, f, ensure_ascii=False, indent=2)
        
        # 保存CSV格式
        all_qa_csv_file = os.path.join(output_dir, 'all_qa.csv')
        with open(all_qa_csv_file, 'w', encoding='utf-8') as f:
            f.write("question,answer\n")
            for qa in all_qa_pairs:
                question = qa['question'].replace('"', '""')
                answer = qa['answer'].replace('"', '""')
                f.write(f'"{question}","{answer}"\n')
        
        # 更新信息库的更新时间
        try:
            repository_manager.update_repository(repository_name, {
                'updated_at': datetime.now().isoformat()
            })
        except Exception as e:
            logging.error(f"更新信息库更新时间失败: {str(e)}")
        
        # 更新任务状态
        with process_lock:
            process_status[task_id]['status'] = 'completed'
            process_status[task_id]['end_time'] = datetime.now().isoformat()
        
        logging.info(f"问答对生成任务 {task_id} 已完成，信息库: {repository_name}, 总问答对数: {len(all_qa_pairs)}")
    
    except Exception as e:
        # 更新任务状态为失败
        with process_lock:
            process_status[task_id]['status'] = 'failed'
            process_status[task_id]['error'] = str(e)
            process_status[task_id]['end_time'] = datetime.now().isoformat()
        
        logging.error(f"问答对生成任务 {task_id} 失败: {str(e)}")

def _generate_qa_pairs(content, llm_config=None):
    """
    生成问答对
    
    Args:
        content: 要生成问答对的内容
        llm_config: LLM配置（可选）
        
    Returns:
        qa_pairs: 生成的问答对列表
    """
    # 合并LLM配置
    merged_config = config.copy()
    if llm_config:
        merged_config.update(llm_config)
    
    # 获取LLM配置
    provider = merged_config.get('provider', 'openai')
    
    # 获取提供商特定配置
    provider_config = merged_config.get(provider, {})
    api_key = provider_config.get('api_key', merged_config.get('api_key', ''))
    model = provider_config.get('model', merged_config.get('model', 'gpt-3.5-turbo'))
    
    # 获取API基础URL
    api_base_urls = {
        'openai': 'https://api.openai.com/v1/chat/completions',
        'qwen': 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions',
        'deepseek': 'https://api.deepseek.com/v1/chat/completions'
    }
    api_base_url = api_base_urls.get(provider, api_base_urls['openai'])
    
    # 获取提示词
    qa_prompt = merged_config.get('qa_prompt', '请根据以下内容生成5-10个问答对，每个问答对应包含一个问题和对应的答案。返回JSON格式，格式为[{"question": "问题", "answer": "答案"}, ...]：')
    qa_system_prompt = merged_config.get('qa_system_prompt', '你是一个专业的问答对生成助手，擅长根据文本内容生成高质量的问题和答案对。')
    
    # 准备请求数据
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    # 特殊处理Qwen API
    if provider == 'qwen':
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'X-DashScope-SSE': 'disable'
        }
    
    data = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': qa_system_prompt},
            {'role': 'user', 'content': f"{qa_prompt}\n\n{content}"}
        ],
        'temperature': merged_config.get('temperature', 0.7),
        'max_tokens': merged_config.get('max_tokens', 2000)
    }
    
    # 发送请求
    response = requests.post(api_base_url, headers=headers, json=data)
    
    # 检查响应
    if response.status_code != 200:
        error_msg = f"API请求失败: {response.status_code} {response.text}"
        logging.error(error_msg)
        raise Exception(error_msg)
    
    # 解析响应
    response_data = response.json()
    
    # 提取问答对
    if provider == 'openai' or provider == 'deepseek' or provider == 'qwen':
        qa_text = response_data['choices'][0]['message']['content']
    else:
        qa_text = response_data['choices'][0]['message']['content']
    
    # 解析JSON
    try:
        # 尝试直接解析
        qa_pairs = json.loads(qa_text)
    except json.JSONDecodeError:
        # 如果直接解析失败，尝试提取JSON部分
        import re
        json_match = re.search(r'\[.*\]', qa_text, re.DOTALL)
        if json_match:
            try:
                qa_pairs = json.loads(json_match.group(0))
            except:
                # 如果仍然失败，返回空列表
                logging.error(f"解析问答对JSON失败: {qa_text}")
                qa_pairs = []
        else:
            logging.error(f"未找到问答对JSON: {qa_text}")
            qa_pairs = []
    
    # 验证格式
    valid_qa_pairs = []
    for qa in qa_pairs:
        if isinstance(qa, dict) and 'question' in qa and 'answer' in qa:
            valid_qa_pairs.append({
                'question': qa['question'],
                'answer': qa['answer']
            })
    
    return valid_qa_pairs

def get_process_status(task_id):
    """
    获取预处理任务状态
    
    Args:
        task_id: 任务ID
        
    Returns:
        status: 任务状态
    """
    with process_lock:
        if task_id in process_status:
            return process_status[task_id]
        else:
            return None
