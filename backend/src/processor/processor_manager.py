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
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# 导入工具模块
from ..utils import file_utils, token_utils
from ..utils.task_manager import task_manager
from ..repository import repository_manager

# 全局配置
config = {}
# 预处理状态
process_status = {}
# 处理锁
process_lock = threading.Lock()

# 创建专用于总结生成的锁
summary_lock = threading.Lock()

# 创建专用于QA生成的锁
qa_lock = threading.Lock()

def init(app_config):
    """
    初始化预处理管理器
    
    Args:
        app_config: 应用配置
    """
    global config
    
    # 加载预处理配置
    processor_config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                        'config', 'config.yaml')
    
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
    
    # 在任务管理器中创建任务
    task_manager.create_task(task_id, 'token', repository_name)
    
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
    Token计算工作线程（修改版）

    Args:
        task_id: 任务ID
        repository_name: 信息库名称
    """
    try:
        # 更新任务状态为运行中
        task_manager.update_task(task_id, status='running')
        
        # 获取信息库目录
        repository_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'data', 'crawled_data', repository_name
        )

        # 检查目录是否存在
        if not os.path.exists(repository_dir):
            raise FileNotFoundError(f"信息库目录不存在: {repository_dir}")

        # 创建token_count目录
        token_count_dir = os.path.join(repository_dir, 'token_count')
        os.makedirs(token_count_dir, exist_ok=True)

        # 删除旧的统计文件
        for filename in os.listdir(token_count_dir):
            if filename.startswith('token_count_') and filename.endswith('.txt'):
                file_path = os.path.join(token_count_dir, filename)
                try:
                    os.remove(file_path)
                except Exception as e:
                    logging.error(f"删除旧文件失败: {file_path}, 错误: {str(e)}")

        # 获取所有支持的文件类型
        supported_file_types = config.get('supported_file_types', ['.txt', '.pdf', '.html'])
        all_files = file_utils.list_files(repository_dir, supported_file_types)
        
        # 过滤掉token_count文件夹下的文件和其他需要忽略的文件
        filtered_files = []
        ignored_filenames = config.get('ignored_filenames', [])
        
        for file_path in all_files:
            file_name = os.path.basename(file_path)
            
            # 检查是否在token_count文件夹中
            if 'token_count' in file_path:
                logging.info(f"跳过token_count文件夹中的文件: {file_name}")
                continue
                
            # 检查是否在忽略列表中
            if file_name in ignored_filenames:
                logging.info(f"跳过忽略列表中的文件: {file_name}")
                continue
                
            filtered_files.append(file_path)
        
        files = filtered_files
        logging.info(f"找到 {len(files)} 个需要处理的文件（已过滤token_count和忽略文件）")

        # 更新任务状态
        with process_lock:
            process_status[task_id]['total_files'] = len(files)
        task_manager.update_task(task_id, metadata={'total_files': len(files)})

        # 为多种模型准备tokenizer
        tokenizers = {
            'token_count_gpt4o': token_utils.get_tokenizer('openai'),
            'token_count_deepseek': token_utils.get_tokenizer('deepseek'),
            'token_count_jina': token_utils.get_tokenizer('jina'),
        }

        token_counts = {k: 0 for k in tokenizers}
        token_tracker_paths = {
            k: os.path.join(token_count_dir, f"{k}.txt") for k in tokenizers
        }

        # 处理每个文件
        processed_files = 0
        for file_path in files:
            try:
                content = file_utils.read_file(file_path)

                for key, tokenizer in tokenizers.items():
                    tokens = token_utils.count_tokens(content, tokenizer)
                    token_counts[key] += tokens
                    # 立即写入每个文件的统计结果
                    with open(token_tracker_paths[key], 'a', encoding='utf-8') as f:
                        f.write(f"{os.path.basename(file_path)}: {tokens}\n")

                processed_files += 1
                with process_lock:
                    process_status[task_id]['processed_files'] = processed_files
                    process_status[task_id]['total_tokens'] = sum(token_counts.values())
                
                # 更新任务进度
                progress = int((processed_files / len(files)) * 100)
                task_manager.update_task(task_id, progress=progress, 
                                       metadata={'processed_files': processed_files})

            except Exception as e:
                logging.error(f"处理文件失败: {file_path}, 错误: {str(e)}")

        # 写入最终统计结果（包含总Token数）
        for key, count in token_counts.items():
            with open(token_tracker_paths[key], 'a', encoding='utf-8') as f:
                # 直接追加总Token数（不添加额外空行）
                f.write(f"总Token数: {count}\n")

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
        
        # 更新任务管理器中的任务状态
        task_manager.update_task(task_id, status='completed', progress=100,
                               result={'token_counts': token_counts})

        logging.info(
            f"Token计算任务 {task_id} 已完成，信息库: {repository_name}, 总Token数: {sum(token_counts.values())}"
        )

    except Exception as e:
        # 更新任务状态为失败
        with process_lock:
            process_status[task_id]['status'] = 'failed'
            process_status[task_id]['error'] = str(e)
            process_status[task_id]['end_time'] = datetime.now().isoformat()
        
        # 更新任务管理器中的任务状态
        task_manager.update_task(task_id, status='failed', error=str(e))

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
    
    # 在任务管理器中创建任务
    task_manager.create_task(task_id, 'summary', repository_name)
    
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
    内容总结工作线程（多线程版本）
    
    Args:
        task_id: 任务ID
        repository_name: 信息库名称
        llm_config: LLM配置（可选）
    """
    try:
        # 更新任务状态为运行中
        task_manager.update_task(task_id, status='running')
        
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
        
        # 获取所有支持的文件类型
        supported_file_types = config.get('supported_file_types', ['.txt', '.pdf', '.html'])
        all_files = file_utils.list_files(repository_dir, supported_file_types)
        
        # 过滤掉token_count文件夹下的文件和其他需要忽略的文件
        filtered_files = []
        ignored_filenames = config.get('ignored_filenames', [])
        
        for file_path in all_files:
            file_name = os.path.basename(file_path)
            
            # 检查是否在token_count文件夹中
            if 'token_count' in file_path:
                logging.info(f"跳过token_count文件夹中的文件: {file_name}")
                continue
                
            # 检查是否在忽略列表中
            if file_name in ignored_filenames:
                logging.info(f"跳过忽略列表中的文件: {file_name}")
                continue
                
            filtered_files.append(file_path)
        
        files = filtered_files
        logging.info(f"找到 {len(files)} 个需要处理的文件（已过滤token_count和忽略文件）")

        # 更新任务状态
        with process_lock:
            process_status[task_id]['total_files'] = len(files)
        task_manager.update_task(task_id, metadata={'total_files': len(files)})
        
        # 获取内容哈希记录
        content_hashes_path = os.path.join(output_dir, 'content_hashes.json')
        content_hashes = {}
        if os.path.exists(content_hashes_path):
            try:
                with open(content_hashes_path, 'r', encoding='utf-8') as f:
                    content_hashes = json.load(f)
                logging.info(f"加载了 {len(content_hashes)} 个文件的内容哈希记录")
            except:
                content_hashes = {}
        
        # 统计处理情况（使用线程安全的计数器）
        processing_stats = {
            'processed_files': 0,
            'skipped_files': 0,
            'new_files': 0,
            'updated_files': 0,
            'failed_files': 0
        }
        
        # 存储所有总结的线程安全列表
        all_summaries = []
        summaries_lock = threading.Lock()
        
        # 获取提示词
        if repository_name:
            try:
                repo_prompt_config = repository_manager.get_merged_prompt_config(repository_name, config)
                summary_prompt = repo_prompt_config.get('summary_prompt', config.get('summary_prompt', '请对以下内容进行总结，突出关键信息：'))
                summary_system_prompt = repo_prompt_config.get('summary_system_prompt', config.get('summary_system_prompt', '你是一个专业的文档总结助手，擅长提取文本中的关键信息并生成简洁明了的总结。'))
            except Exception as e:
                logging.warning(f"获取信息库Prompt配置失败，使用全局配置: {str(e)}")
                summary_prompt = config.get('summary_prompt', '请对以下内容进行总结，突出关键信息：')
                summary_system_prompt = config.get('summary_system_prompt', '你是一个专业的文档总结助手，擅长提取文本中的关键信息并生成简洁明了的总结。')
        else:
            summary_prompt = config.get('summary_prompt', '请对以下内容进行总结，突出关键信息：')
            summary_system_prompt = config.get('summary_system_prompt', '你是一个专业的文档总结助手，擅长提取文本中的关键信息并生成简洁明了的总结。')
        
        def process_single_file(file_path):
            """处理单个文件的总结生成"""
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
                        with summaries_lock:
                            all_summaries.append(f"## {os.path.splitext(file_name)[0]}\n\n{summary}\n\n")
                    
                    return {'status': 'skipped', 'file_name': file_name}
                
                # 判断是新文件还是更新文件
                if file_name in content_hashes:
                    logging.info(f"文件内容已更新，重新生成总结: {file_name}")
                    file_status = 'updated'
                else:
                    logging.info(f"新文件，生成总结: {file_name}")
                    file_status = 'new'
                
                # 生成总结
                summary = _generate_summary(content, llm_config, repository_name)
                
                # 保存总结
                summary_file = os.path.join(output_dir, f"{os.path.splitext(file_name)[0]}_summary.txt")
                with open(summary_file, 'w', encoding='utf-8') as f:
                    f.write(summary)
                
                # 线程安全地添加到总结集合
                with summaries_lock:
                    all_summaries.append(f"## {os.path.splitext(file_name)[0]}\n\n{summary}\n\n")
                
                # 线程安全地更新内容哈希
                with summaries_lock:
                    content_hashes[file_name] = content_hash
                
                return {'status': file_status, 'file_name': file_name}
                
            except Exception as e:
                logging.error(f"处理文件失败: {file_path}, 错误: {str(e)}")
                return {'status': 'failed', 'file_name': file_name, 'error': str(e)}
        
        # 确定线程数：最多128个线程，但不超过文件数量
        max_workers = min(128, len(files), config.get('max_summary_threads', 64))
        logging.info(f"使用 {max_workers} 个线程并发生成总结")
        
        # 使用ThreadPoolExecutor进行多线程处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_file = {executor.submit(process_single_file, file_path): file_path for file_path in files}
            
            # 处理完成的任务
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    
                    # 更新统计信息
                    with summary_lock:
                        processing_stats['processed_files'] += 1
                        if result['status'] == 'skipped':
                            processing_stats['skipped_files'] += 1
                        elif result['status'] == 'new':
                            processing_stats['new_files'] += 1
                        elif result['status'] == 'updated':
                            processing_stats['updated_files'] += 1
                        elif result['status'] == 'failed':
                            processing_stats['failed_files'] += 1
                        
                        # 更新进度
                        progress = int((processing_stats['processed_files'] / len(files)) * 100)
                        
                        # 更新任务状态
                        with process_lock:
                            process_status[task_id]['processed_files'] = processing_stats['processed_files']
                        
                        # 更新任务管理器
                        task_manager.update_task(task_id, progress=progress, metadata=processing_stats.copy())
                        
                        if processing_stats['processed_files'] % 10 == 0:  # 每处理10个文件输出一次进度
                            logging.info(f"总结生成进度: {processing_stats['processed_files']}/{len(files)} ({progress}%)")
                
                except Exception as e:
                    logging.error(f"处理文件任务失败: {file_path}, 错误: {str(e)}")
                    with summary_lock:
                        processing_stats['processed_files'] += 1
                        processing_stats['failed_files'] += 1
        
        # 保存内容哈希记录
        with open(content_hashes_path, 'w', encoding='utf-8') as f:
            json.dump(content_hashes, f, indent=2)
        
        # 保存总结合集
        all_summaries_file = os.path.join(output_dir, 'all_summaries.txt')
        with open(all_summaries_file, 'w', encoding='utf-8') as f:
            f.write("# 信息库总结\n\n")
            f.write(f"信息库: {repository_name}\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"并发线程数: {max_workers}\n\n")
            f.write("---\n\n")
            f.write("".join(all_summaries))
        
        # 更新信息库的更新时间
        try:
            repository_manager.update_repository(repository_name, {
                'updated_at': datetime.now().isoformat()
            })
        except Exception as e:
            logging.error(f"更新信息库更新时间失败: {str(e)}")
        
        # 自动计算总结文件的Token数量
        if processing_stats['new_files'] > 0 or processing_stats['updated_files'] > 0:
            logging.info("总结生成完成，开始自动计算Token...")
            try:
                _calculate_summary_tokens(repository_name, output_dir)
                logging.info("总结文件Token计算完成")
            except Exception as e:
                logging.error(f"自动计算总结文件Token失败: {str(e)}")
        
        # 更新任务状态
        with process_lock:
            process_status[task_id]['status'] = 'completed'
            process_status[task_id]['end_time'] = datetime.now().isoformat()
        
        # 更新任务管理器中的任务状态
        task_manager.update_task(task_id, status='completed', progress=100, result=processing_stats)
        
        logging.info(f"多线程内容总结任务 {task_id} 已完成，信息库: {repository_name}")
        logging.info(f"使用了 {max_workers} 个并发线程")
        logging.info(f"处理统计 - 总文件数: {len(files)}, 已处理: {processing_stats['processed_files']}, 跳过: {processing_stats['skipped_files']}, 新文件: {processing_stats['new_files']}, 更新文件: {processing_stats['updated_files']}, 失败: {processing_stats['failed_files']}")
    
    except Exception as e:
        # 更新任务状态为失败
        with process_lock:
            process_status[task_id]['status'] = 'failed'
            process_status[task_id]['error'] = str(e)
            process_status[task_id]['end_time'] = datetime.now().isoformat()
        
        # 更新任务管理器中的任务状态
        task_manager.update_task(task_id, status='failed', error=str(e))
        
        logging.error(f"多线程内容总结任务 {task_id} 失败: {str(e)}")

def _generate_summary(content, llm_config=None, repository_name=None):
    """
    生成内容总结（支持大文件切割）
    
    Args:
        content: 要总结的内容
        llm_config: LLM配置（可选）
        repository_name: 信息库名称（可选）
        
    Returns:
        summary: 生成的总结
    """
    try:
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
        
        if not api_key:
            raise ValueError(f"未设置{provider}的API密钥")
        
        # 检查文件大小，如果超过55000 tokens则进行切割
        from ..utils import token_utils
        tokenizer = token_utils.get_tokenizer('openai')  # 使用GPT4o tokenizer
        total_tokens = token_utils.count_tokens(content, tokenizer)
        
        if total_tokens > 55000:
            logging.info(f"文件过大（{total_tokens} tokens），开始分块处理...")
            
            # 切割内容为不超过55000 tokens的块
            chunks = _chunk_content_for_summary(content, 55000)
            logging.info(f"文件已分割为 {len(chunks)} 个块")
            
            # 分别为每个块生成总结
            chunk_summaries = []
            for i, chunk in enumerate(chunks):
                logging.info(f"处理第 {i+1}/{len(chunks)} 块...")
                chunk_summary = _generate_single_summary(chunk, merged_config, provider, api_key, model, repository_name)
                chunk_summaries.append(chunk_summary)
                logging.info(f"第 {i+1} 块总结完成")
            
            # 合并所有块的总结
            logging.info("开始合并块总结...")
            combined_content = "\n\n".join([f"## 部分 {i+1}\n{summary}" for i, summary in enumerate(chunk_summaries)])
            
            # 对合并后的总结再次进行总结
            final_summary = _generate_final_summary(combined_content, merged_config, provider, api_key, model, repository_name)
            logging.info("大文件总结合并完成")
            
            return final_summary
        else:
            # 文件不大，直接处理
            return _generate_single_summary(content, merged_config, provider, api_key, model, repository_name)
    
    except Exception as e:
        logging.error(f"生成总结失败: {str(e)}")
        raise

def _chunk_content_for_summary(content, max_tokens):
    """
    为总结生成切割内容
    
    Args:
        content: 要切割的内容
        max_tokens: 最大token数
        
    Returns:
        chunks: 内容块列表
    """
    from ..utils import token_utils
    
    # 获取tokenizer
    tokenizer = token_utils.get_tokenizer('openai')
    
    # 如果内容不超过最大限制，直接返回
    total_tokens = token_utils.count_tokens(content, tokenizer)
    if total_tokens <= max_tokens:
        return [content]
    
    # 按段落分割内容（优先保持段落完整性）
    import re
    # 按双换行符分割段落
    paragraphs = re.split(r'\n\s*\n', content)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    
    chunks = []
    current_chunk = ""
    current_tokens = 0
    
    for paragraph in paragraphs:
        paragraph_tokens = token_utils.count_tokens(paragraph, tokenizer)
        
        # 如果单个段落就超过最大限制，按句子进一步分割
        if paragraph_tokens > max_tokens:
            # 先保存当前块
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
                current_tokens = 0
            
            # 按句子分割大段落
            sentences = re.split(r'[。！？\n]+', paragraph)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            for sentence in sentences:
                sentence_tokens = token_utils.count_tokens(sentence, tokenizer)
                
                # 如果单句还是太长，直接作为一个块
                if sentence_tokens > max_tokens:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                        current_chunk = ""
                        current_tokens = 0
                    chunks.append(sentence)
                    continue
                
                # 检查加上这句话是否会超限
                if current_tokens + sentence_tokens > max_tokens and current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                    current_tokens = sentence_tokens
                else:
                    if current_chunk:
                        current_chunk += "。" + sentence
                    else:
                        current_chunk = sentence
                    current_tokens += sentence_tokens
            
            continue
        
        # 检查加上这个段落是否会超过限制
        if current_tokens + paragraph_tokens > max_tokens and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = paragraph
            current_tokens = paragraph_tokens
        else:
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
            current_tokens += paragraph_tokens
    
    # 保存最后一块
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    # 记录分块结果
    logging.info(f"内容分块完成：总tokens {total_tokens}，目标块大小 {max_tokens}，实际分成 {len(chunks)} 块")
    for i, chunk in enumerate(chunks):
        chunk_tokens = token_utils.count_tokens(chunk, tokenizer)
        logging.info(f"  块 {i+1}: {chunk_tokens} tokens")
    
    return chunks

def _generate_single_summary(content, merged_config, provider, api_key, model, repository_name):
    """
    生成单个内容块的总结
    
    Args:
        content: 要总结的内容
        merged_config: 合并后的配置
        provider: LLM提供商
        api_key: API密钥
        model: 模型名称
        repository_name: 信息库名称
        
    Returns:
        summary: 生成的总结
    """
    # 获取API基础URL
    api_base_urls = {
        'openai': 'https://api.openai.com/v1/chat/completions',
        'qwen': 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions',
        'deepseek': 'https://api.deepseek.com/v1/chat/completions'
    }
    api_base_url = api_base_urls.get(provider, api_base_urls['openai'])
    
    # 获取提示词
    # 如果提供了信息库名称，获取信息库级别的Prompt配置
    if repository_name:
        try:
            repo_prompt_config = repository_manager.get_merged_prompt_config(repository_name, merged_config)
            # 使用信息库级别的Prompt配置
            summary_prompt = repo_prompt_config.get('summary_prompt', merged_config.get('summary_prompt', '请对以下内容进行总结，突出关键信息：'))
            summary_system_prompt = repo_prompt_config.get('summary_system_prompt', merged_config.get('summary_system_prompt', '你是一个专业的文档总结助手，擅长提取文本中的关键信息并生成简洁明了的总结。'))
        except Exception as e:
            logging.warning(f"获取信息库Prompt配置失败，使用全局配置: {str(e)}")
            summary_prompt = merged_config.get('summary_prompt', '请对以下内容进行总结，突出关键信息：')
            summary_system_prompt = merged_config.get('summary_system_prompt', '你是一个专业的文档总结助手，擅长提取文本中的关键信息并生成简洁明了的总结。')
    else:
        # 使用全局配置
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
    
    # 发送请求，增加超时时间并添加重试机制
    max_retries = 3
    timeout = 900  # 15分钟
    
    for attempt in range(max_retries):
        try:
            response = requests.post(api_base_url, headers=headers, json=data, timeout=timeout)
            
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
            
            # 清理和格式化总结
            summary = summary.strip()
            
            return summary
            
        except requests.exceptions.Timeout as e:
            logging.warning(f"总结生成超时 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            if attempt == max_retries - 1:
                raise Exception(f"总结生成超时，已重试 {max_retries} 次")
            # 等待一段时间后重试
            import time
            time.sleep(5 * (attempt + 1))  # 递增等待时间
            
        except requests.exceptions.RequestException as e:
            logging.warning(f"网络请求失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            if attempt == max_retries - 1:
                raise Exception(f"网络请求失败，已重试 {max_retries} 次: {str(e)}")
            # 等待一段时间后重试
            import time
            time.sleep(3 * (attempt + 1))

def _generate_final_summary(combined_content, merged_config, provider, api_key, model, repository_name):
    """
    生成最终合并总结
    
    Args:
        combined_content: 已合并的块总结内容
        merged_config: 合并后的配置
        provider: LLM提供商
        api_key: API密钥
        model: 模型名称
        repository_name: 信息库名称
        
    Returns:
        final_summary: 最终总结
    """
    # 获取API基础URL
    api_base_urls = {
        'openai': 'https://api.openai.com/v1/chat/completions',
        'qwen': 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions',
        'deepseek': 'https://api.deepseek.com/v1/chat/completions'
    }
    api_base_url = api_base_urls.get(provider, api_base_urls['openai'])
    
    # 合并总结的特殊提示词
    merge_prompt = """请将以下分段总结合并为一个完整、连贯的总结。
要求：
1. 保持所有重要信息
2. 去除重复内容
3. 确保逻辑连贯
4. 突出关键要点

分段总结内容："""
    
    merge_system_prompt = "你是一个专业的文档整理助手，擅长将多个分段总结合并为一个完整、连贯的总结文档。"
    
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
            {'role': 'system', 'content': merge_system_prompt},
            {'role': 'user', 'content': f"{merge_prompt}\n\n{combined_content}"}
        ],
        'temperature': merged_config.get('temperature', 0.2),
        'max_tokens': merged_config.get('max_tokens', 3000)  # 合并总结可能需要更多token
    }
    
    # 发送请求
    max_retries = 3
    timeout = 900
    
    for attempt in range(max_retries):
        try:
            response = requests.post(api_base_url, headers=headers, json=data, timeout=timeout)
            
            # 检查响应
            if response.status_code != 200:
                error_msg = f"合并总结API请求失败: {response.status_code} {response.text}"
                logging.error(error_msg)
                raise Exception(error_msg)
            
            # 解析响应
            response_data = response.json()
            
            # 提取最终总结
            if provider == 'openai' or provider == 'deepseek' or provider == 'qwen':
                final_summary = response_data['choices'][0]['message']['content']
            else:
                final_summary = response_data['choices'][0]['message']['content']
            
            # 清理和格式化总结
            final_summary = final_summary.strip()
            
            return final_summary
            
        except requests.exceptions.Timeout as e:
            logging.warning(f"合并总结超时 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            if attempt == max_retries - 1:
                raise Exception(f"合并总结超时，已重试 {max_retries} 次")
            import time
            time.sleep(5 * (attempt + 1))
            
        except requests.exceptions.RequestException as e:
            logging.warning(f"合并总结请求失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            if attempt == max_retries - 1:
                raise Exception(f"合并总结请求失败，已重试 {max_retries} 次: {str(e)}")
            import time
            time.sleep(3 * (attempt + 1))

def start_qa_generation(repository_name, llm_config=None, use_summary_files=None):
    """
    开始问答对生成任务
    
    Args:
        repository_name: 信息库名称
        llm_config: LLM配置（可选）
        use_summary_files: 是否使用总结文件（True=基于总结，False=基于原始文件，None=自动判断）
        
    Returns:
        task_id: 任务ID
    """
    # 生成任务ID
    task_id = f"qa_{int(time.time())}"
    
    # 在任务管理器中创建任务
    task_manager.create_task(task_id, 'qa', repository_name)
    
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
        'use_summary_files': use_summary_files,
        'error': None
    }
    
    # 创建并启动处理线程
    process_thread = threading.Thread(
        target=_qa_generation_worker,
        args=(task_id, repository_name, llm_config, use_summary_files)
    )
    process_thread.daemon = True
    process_thread.start()
    
    logging.info(f"问答对生成任务 {task_id} 已启动，信息库: {repository_name}, 使用总结文件: {use_summary_files}")
    
    return task_id

def _qa_generation_worker(task_id, repository_name, llm_config=None, use_summary_files=None):
    """
    问答对生成工作线程（多线程版本）
    
    Args:
        task_id: 任务ID
        repository_name: 信息库名称
        llm_config: LLM配置（可选）
        use_summary_files: 是否使用总结文件（True=基于总结，False=基于原始文件，None=自动判断）
    """
    try:
        # 更新任务状态为运行中
        task_manager.update_task(task_id, status='running')
        
        # 获取信息库目录
        repository_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                     'data', 'crawled_data', repository_name)
        
        # 检查目录是否存在
        if not os.path.exists(repository_dir):
            raise FileNotFoundError(f"信息库目录不存在: {repository_dir}")
        
        # 创建输出目录 - 按照qa_generator.py的结构
        base_output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                      'data', 'qa_generator_output')
        json_output_dir = os.path.join(base_output_dir, 'json_output', f"{repository_name}_json_qa")
        csv_output_dir = os.path.join(base_output_dir, 'csv_output', f"{repository_name}_csv_qa")
        os.makedirs(json_output_dir, exist_ok=True)
        os.makedirs(csv_output_dir, exist_ok=True)
        
        # 如果明确指定了生成模式，清除现有的问答对文件
        if use_summary_files is not None:
            logging.info(f"清除现有问答对文件，准备基于{'总结文件' if use_summary_files else '原始文件'}生成")
            # 清除JSON输出目录中的问答对文件
            for filename in os.listdir(json_output_dir):
                if filename.endswith('.json') and filename != 'content_hashes.json':
                    file_path = os.path.join(json_output_dir, filename)
                    try:
                        os.remove(file_path)
                        logging.info(f"已删除旧问答对文件: {filename}")
                    except Exception as e:
                        logging.error(f"删除文件失败: {file_path}, 错误: {str(e)}")
            
            # 清除CSV输出目录中的问答对文件
            for filename in os.listdir(csv_output_dir):
                if filename.endswith('.csv'):
                    file_path = os.path.join(csv_output_dir, filename)
                    try:
                        os.remove(file_path)
                        logging.info(f"已删除旧问答对文件: {filename}")
                    except Exception as e:
                        logging.error(f"删除文件失败: {file_path}, 错误: {str(e)}")
            
            # 清除内容哈希记录
            content_hashes_path = os.path.join(json_output_dir, 'content_hashes.json')
            if os.path.exists(content_hashes_path):
                try:
                    os.remove(content_hashes_path)
                    logging.info("已清除内容哈希记录")
                except Exception as e:
                    logging.error(f"删除内容哈希记录失败: {str(e)}")
        
        # 检查是否有总结文件，优先使用总结文件
        summary_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                  'data', 'summarizer_output', repository_name)
        
        files = []
        
        # 根据use_summary_files参数明确选择文件源
        if use_summary_files is True:
            # 强制使用总结文件
            if os.path.exists(summary_dir):
                summary_files = file_utils.list_files(summary_dir, ['.txt'])
                # 过滤掉不需要的文件
                filtered_summary_files = []
                for file_path in summary_files:
                    file_name = os.path.basename(file_path)
                    # 跳过特殊文件
                    if file_name in ['all_summaries.txt', 'content_hashes.json'] or \
                       file_name.startswith('token_count_'):
                        continue
                    if '_summarized.txt' in file_name or file_name.endswith('_summary.txt'):
                        filtered_summary_files.append(file_path)
                
                if filtered_summary_files:
                    files = filtered_summary_files
                    use_summary_files = True
                    logging.info(f"强制使用总结文件进行QA生成，共 {len(files)} 个文件")
                else:
                    raise FileNotFoundError("未找到总结文件，请先生成总结")
            else:
                raise FileNotFoundError("总结目录不存在，请先生成总结")
        
        elif use_summary_files is False:
            # 强制使用原始文件
            supported_file_types = config.get('supported_file_types', ['.txt', '.pdf', '.html'])
            all_files = file_utils.list_files(repository_dir, supported_file_types)
            
            # 过滤掉token_count文件夹下的文件和其他需要忽略的文件
            filtered_files = []
            ignored_filenames = config.get('ignored_filenames', [])
            
            for file_path in all_files:
                file_name = os.path.basename(file_path)
                
                # 检查是否在token_count文件夹中
                if 'token_count' in file_path:
                    logging.info(f"跳过token_count文件夹中的文件: {file_name}")
                    continue
                    
                # 检查是否在忽略列表中
                if file_name in ignored_filenames:
                    logging.info(f"跳过忽略列表中的文件: {file_name}")
                    continue
                    
                filtered_files.append(file_path)
            
            files = filtered_files
            use_summary_files = False
            logging.info(f"强制使用原始文件进行QA生成，共 {len(files)} 个文件（已过滤token_count和忽略文件）")
        
        else:
            # 自动判断模式（保持原有逻辑）
            if os.path.exists(summary_dir):
                # 获取总结文件
                summary_files = file_utils.list_files(summary_dir, ['.txt'])
                # 过滤掉不需要的文件
                filtered_summary_files = []
                for file_path in summary_files:
                    file_name = os.path.basename(file_path)
                    # 跳过特殊文件
                    if file_name in ['all_summaries.txt', 'content_hashes.json'] or \
                       file_name.startswith('token_count_'):
                        continue
                    if '_summarized.txt' in file_name or file_name.endswith('_summary.txt'):
                        filtered_summary_files.append(file_path)
                
                if filtered_summary_files:
                    files = filtered_summary_files
                    use_summary_files = True
                    logging.info(f"自动选择总结文件进行QA生成，共 {len(files)} 个文件")
            
            if not files:
                # 使用原始文件
                supported_file_types = config.get('supported_file_types', ['.txt', '.pdf', '.html'])
                all_files = file_utils.list_files(repository_dir, supported_file_types)
                
                # 过滤掉token_count文件夹下的文件和其他需要忽略的文件
                filtered_files = []
                ignored_filenames = config.get('ignored_filenames', [])
                
                for file_path in all_files:
                    file_name = os.path.basename(file_path)
                    
                    # 检查是否在token_count文件夹中
                    if 'token_count' in file_path:
                        logging.info(f"跳过token_count文件夹中的文件: {file_name}")
                        continue
                        
                    # 检查是否在忽略列表中
                    if file_name in ignored_filenames:
                        logging.info(f"跳过忽略列表中的文件: {file_name}")
                        continue
                        
                    filtered_files.append(file_path)
                
                files = filtered_files
                use_summary_files = False
                logging.info(f"自动选择原始文件进行QA生成，共 {len(files)} 个文件（已过滤token_count和忽略文件）")
        
        # 更新任务状态
        with process_lock:
            process_status[task_id]['total_files'] = len(files)
        task_manager.update_task(task_id, metadata={'total_files': len(files)})
        
        # 获取分块大小配置
        merged_config = config.copy()
        if llm_config:
            merged_config.update(llm_config)
        
        # 从信息库级别配置获取分块大小
        if repository_name:
            try:
                from ..repository import repository_manager
                repo_prompt_config = repository_manager.get_merged_prompt_config(repository_name, merged_config)
                # 使用信息库级别的分块配置
                qa_stages = repo_prompt_config.get('qa_stages', {})
                chunk_config = qa_stages.get('chunk', {})
                chunk_size = chunk_config.get('chunk_size', 1000)
                logging.info(f"使用信息库级别的分块大小: {chunk_size} tokens")
            except Exception as e:
                logging.warning(f"获取信息库分块配置失败，使用全局配置: {str(e)}")
                # 从全局配置获取分块大小 - 修复配置路径
                processor_config = merged_config.get('processor', {})
                qa_stages = processor_config.get('qa_stages', {})
                chunk_config = qa_stages.get('chunk', {})
                chunk_size = chunk_config.get('chunk_size', 1000)
                logging.info(f"使用全局分块大小: {chunk_size} tokens")
        else:
            # 从全局配置获取分块大小 - 修复配置路径
            processor_config = merged_config.get('processor', {})
            qa_stages = processor_config.get('qa_stages', {})
            chunk_config = qa_stages.get('chunk', {})
            chunk_size = chunk_config.get('chunk_size', 1000)
            logging.info(f"使用全局分块大小: {chunk_size} tokens")
        
        # 检查Token计算状态
        token_count_dir = os.path.join(repository_dir, 'token_count')
        token_file_path = os.path.join(token_count_dir, 'token_count_deepseek.txt')
        
        # 移除强制Token计算依赖，让基于总结文件的QA生成随时可用
        # 如果使用总结文件但没有Token计算，尝试计算Token（非强制）
        if use_summary_files and not os.path.exists(token_file_path):
            logging.info("总结文件缺少Token计算，尝试计算（非强制）...")
            try:
                _calculate_summary_tokens(repository_name, summary_dir)
                logging.info("总结文件Token计算完成")
            except Exception as e:
                logging.warning(f"总结文件Token计算失败，但不影响QA生成: {str(e)}")
        
        # 加载Token计算结果（如果存在）
        file_token_map = {}
        if os.path.exists(token_file_path):
            try:
                with open(token_file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if ':' in line and not line.startswith('总Token数'):
                            file_name, token_str = line.split(':', 1)
                            try:
                                tokens = int(token_str.strip())
                                file_token_map[file_name.strip()] = tokens
                            except ValueError:
                                continue
                logging.info(f"加载了 {len(file_token_map)} 个文件的Token信息")
            except Exception as e:
                logging.error(f"读取Token文件失败: {str(e)}")
        else:
            logging.info("未找到Token计算文件，将跳过基于Token的分块优化")
        
        # 获取内容哈希记录
        content_hashes_path = os.path.join(json_output_dir, 'content_hashes.json')
        content_hashes = {}
        if os.path.exists(content_hashes_path):
            try:
                with open(content_hashes_path, 'r', encoding='utf-8') as f:
                    content_hashes = json.load(f)
                logging.info(f"加载了 {len(content_hashes)} 个文件的内容哈希记录")
            except:
                content_hashes = {}
        
        # 统计处理情况（使用线程安全的计数器）
        processing_stats = {
            'processed_files': 0,
            'skipped_files': 0,
            'new_files': 0,
            'updated_files': 0,
            'failed_files': 0,
            'total_qa_pairs': 0
        }
        
        def process_single_file_qa(file_path):
            """处理单个文件的QA生成"""
            try:
                file_name = os.path.basename(file_path)
                
                # 检查是否在token_count文件夹中
                if 'token_count' in file_path:
                    logging.info(f"跳过token_count文件夹中的文件: {file_name}")
                    return {'status': 'skipped', 'file_name': file_name, 'qa_pairs': 0}
                
                # 检查是否在忽略列表中
                ignored_filenames = config.get('ignored_filenames', [])
                if file_name in ignored_filenames:
                    logging.info(f"文件在忽略列表中，跳过处理: {file_name}")
                    return {'status': 'skipped', 'file_name': file_name, 'qa_pairs': 0}
                
                # 读取文件内容
                content = file_utils.read_file(file_path)
                
                # 计算内容哈希
                content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
                
                # 检查是否需要处理
                if config.get('incremental_processing', True) and file_name in content_hashes and content_hashes[file_name] == content_hash:
                    # 文件内容未变，跳过处理
                    logging.info(f"文件内容未变，跳过处理: {file_name}")
                    
                    # 计算已有问答对数量
                    json_file = os.path.join(json_output_dir, f"{os.path.splitext(file_name)[0]}.json")
                    qa_pairs_count = 0
                    if os.path.exists(json_file):
                        try:
                            with open(json_file, 'r', encoding='utf-8') as f:
                                existing_qa_pairs = json.load(f)
                            qa_pairs_count = len(existing_qa_pairs)
                        except:
                            pass
                    
                    return {'status': 'skipped', 'file_name': file_name, 'qa_pairs': qa_pairs_count}
                
                # 判断是新文件还是更新文件
                if file_name in content_hashes:
                    logging.info(f"文件内容已更新，重新生成问答对: {file_name}")
                    file_status = 'updated'
                else:
                    logging.info(f"新文件，生成问答对: {file_name}")
                    file_status = 'new'
                
                # 获取文件的Token数量
                file_tokens = file_token_map.get(file_name, 0)
                
                # 基于Token数量进行分块
                if file_tokens > 0 and file_tokens > chunk_size:
                    # 使用设定的分块大小进行分块
                    chunks = _chunk_content_by_tokens(content, chunk_size)
                    logging.info(f"文件 {file_name} 有 {file_tokens} tokens，分成 {len(chunks)} 块")
                else:
                    # 文件较小，不分块
                    chunks = [content]
                    logging.info(f"文件 {file_name} 较小（{file_tokens} tokens），不分块")
                
                # 第一阶段：为每个块生成问答对
                all_qa_pairs_for_file = []
                logging.info(f"处理文件 {file_name}，共 {len(chunks)} 个块")
                
                for i, chunk in enumerate(chunks):
                    logging.info(f"  处理块 {i+1}/{len(chunks)} (第一阶段：生成问答对)")
                    qa_pairs_chunk = _generate_qa_pairs_for_chunk(chunk, llm_config, repository_name)
                    if qa_pairs_chunk:
                        all_qa_pairs_for_file.extend(qa_pairs_chunk)
                
                if not all_qa_pairs_for_file:
                    logging.warning(f"文件 {file_name} 第一阶段未生成任何问答对")
                    return {'status': 'failed', 'file_name': file_name, 'qa_pairs': 0, 'error': '未生成任何问答对'}
                
                # 保存第一阶段结果
                file_base = os.path.splitext(file_name)[0]
                json_output_path = os.path.join(json_output_dir, f"{file_base}.json")
                with open(json_output_path, 'w', encoding='utf-8') as f:
                    json.dump(all_qa_pairs_for_file, f, ensure_ascii=False, indent=2)
                logging.info(f"  第一阶段完成，生成 {len(all_qa_pairs_for_file)} 个问答对")
                
                # 第二阶段：去重和筛选（Reduce）
                current_qa_pairs = all_qa_pairs_for_file
                processor_config = config.get('processor', {})
                if processor_config.get('qa_stages', {}).get('reduce', {}).get('enabled', True):
                    logging.info(f"  第二阶段：去重和筛选问答对")
                    reduced_qa_pairs = _reduce_qa_pairs_llm(current_qa_pairs, llm_config, repository_name)
                    if reduced_qa_pairs:
                        current_qa_pairs = reduced_qa_pairs
                        # 更新JSON文件
                        with open(json_output_path, 'w', encoding='utf-8') as f:
                            json.dump(current_qa_pairs, f, ensure_ascii=False, indent=2)
                        logging.info(f"  第二阶段完成，保留 {len(current_qa_pairs)} 个问答对")
                    else:
                        logging.warning(f"  第二阶段失败，保留原始问答对")
                
                # 第三阶段：质量评估（Self Evaluation）
                if processor_config.get('qa_stages', {}).get('evaluate', {}).get('enabled', True):
                    logging.info(f"  第三阶段：评估问答对质量")
                    evaluated_qa_pairs = _evaluate_qa_pairs_llm(current_qa_pairs, llm_config, repository_name)
                    if evaluated_qa_pairs:
                        current_qa_pairs = evaluated_qa_pairs
                        # 更新JSON文件
                        with open(json_output_path, 'w', encoding='utf-8') as f:
                            json.dump(current_qa_pairs, f, ensure_ascii=False, indent=2)
                        logging.info(f"  第三阶段完成，评估了 {len(current_qa_pairs)} 个问答对")
                    else:
                        logging.warning(f"  第三阶段失败，保留未评估的问答对")
                
                # 第四阶段：生成CSV文件
                csv_output_path = os.path.join(csv_output_dir, f"{file_base}.csv")
                with open(csv_output_path, 'w', encoding='utf-8') as f:
                    # 写入CSV格式（使用制表符分隔）
                    for qa in current_qa_pairs:
                        question = qa.get('q', '').replace('\n', ' ').replace('\t', ' ')
                        answer = qa.get('a', '').replace('\n', ' ').replace('\t', ' ')
                        f.write(f"{question}\t{answer}\n")
                logging.info(f"  CSV文件已生成: {csv_output_path}")
                
                # 线程安全地更新内容哈希
                with qa_lock:
                    content_hashes[file_name] = content_hash
                
                return {'status': file_status, 'file_name': file_name, 'qa_pairs': len(current_qa_pairs)}
                
            except Exception as e:
                logging.error(f"处理文件失败: {file_path}, 错误: {str(e)}")
                return {'status': 'failed', 'file_name': file_name, 'qa_pairs': 0, 'error': str(e)}
        
        # 确定线程数：最多128个线程，但不超过文件数量
        max_workers = min(128, len(files), config.get('max_qa_threads', 64))
        logging.info(f"使用 {max_workers} 个线程并发生成QA对")
        
        # 使用ThreadPoolExecutor进行多线程处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_file = {executor.submit(process_single_file_qa, file_path): file_path for file_path in files}
            
            # 处理完成的任务
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    
                    # 更新统计信息
                    with qa_lock:
                        processing_stats['processed_files'] += 1
                        processing_stats['total_qa_pairs'] += result['qa_pairs']
                        
                        if result['status'] == 'skipped':
                            processing_stats['skipped_files'] += 1
                        elif result['status'] == 'new':
                            processing_stats['new_files'] += 1
                        elif result['status'] == 'updated':
                            processing_stats['updated_files'] += 1
                        elif result['status'] == 'failed':
                            processing_stats['failed_files'] += 1
                        
                        # 更新进度
                        progress = int((processing_stats['processed_files'] / len(files)) * 100)
                        
                        # 更新任务状态
                        with process_lock:
                            process_status[task_id]['processed_files'] = processing_stats['processed_files']
                            process_status[task_id]['total_qa_pairs'] = processing_stats['total_qa_pairs']
                        
                        # 更新任务管理器
                        task_manager.update_task(task_id, progress=progress, metadata=processing_stats.copy())
                        
                        if processing_stats['processed_files'] % 10 == 0:  # 每处理10个文件输出一次进度
                            logging.info(f"QA生成进度: {processing_stats['processed_files']}/{len(files)} ({progress}%)")
                
                except Exception as e:
                    logging.error(f"处理文件任务失败: {file_path}, 错误: {str(e)}")
                    with qa_lock:
                        processing_stats['processed_files'] += 1
                        processing_stats['failed_files'] += 1
        
        # 保存内容哈希记录
        with open(content_hashes_path, 'w', encoding='utf-8') as f:
            json.dump(content_hashes, f, indent=2)
        
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
        
        # 更新任务管理器中的任务状态
        task_manager.update_task(task_id, status='completed', progress=100, result=processing_stats)
        
        logging.info(f"多线程问答对生成任务 {task_id} 已完成，信息库: {repository_name}")
        logging.info(f"使用了 {max_workers} 个并发线程")
        logging.info(f"处理统计 - 总文件数: {len(files)}, 已处理: {processing_stats['processed_files']}, 跳过: {processing_stats['skipped_files']}, 新文件: {processing_stats['new_files']}, 更新文件: {processing_stats['updated_files']}, 失败: {processing_stats['failed_files']}, 总QA对数: {processing_stats['total_qa_pairs']}")
    
    except Exception as e:
        # 更新任务状态为失败
        with process_lock:
            process_status[task_id]['status'] = 'failed'
            process_status[task_id]['error'] = str(e)
            process_status[task_id]['end_time'] = datetime.now().isoformat()
        
        # 更新任务管理器中的任务状态
        task_manager.update_task(task_id, status='failed', error=str(e))
        
        logging.error(f"多线程问答对生成任务 {task_id} 失败: {str(e)}")

def _chunk_content_by_tokens(content, target_chunk_size):
    """
    基于Token数量将内容分成指定大小的块
    
    Args:
        content: 要分块的内容
        target_chunk_size: 目标块大小（tokens）
        
    Returns:
        chunks: 内容块列表
    """
    # 导入token工具
    from ..utils import token_utils
    
    # 获取tokenizer
    tokenizer = token_utils.get_tokenizer('deepseek')
    
    # 如果内容很短，直接返回
    total_tokens = token_utils.count_tokens(content, tokenizer)
    if total_tokens <= target_chunk_size:
        return [content]
    
    # 按句子分割内容（更细粒度的分割）
    import re
    # 按句号、问号、感叹号、换行符分割
    sentences = re.split(r'[。！？\n]+', content)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    chunks = []
    current_chunk = ""
    current_tokens = 0
    
    for sentence in sentences:
        sentence_tokens = token_utils.count_tokens(sentence, tokenizer)
        
        # 如果单个句子就超过目标大小，单独成块
        if sentence_tokens > target_chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
                current_tokens = 0
            chunks.append(sentence)
            continue
        
        # 如果加上这个句子会超过目标大小，先保存当前块
        if current_tokens + sentence_tokens > target_chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
            current_tokens = sentence_tokens
        else:
            # 添加到当前块
            if current_chunk:
                current_chunk += "。" + sentence
            else:
                current_chunk = sentence
            current_tokens += sentence_tokens
    
    # 保存最后一块
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    # 记录分块结果
    logging.info(f"内容分块完成：总tokens {total_tokens}，目标块大小 {target_chunk_size}，实际分成 {len(chunks)} 块")
    for i, chunk in enumerate(chunks):
        chunk_tokens = token_utils.count_tokens(chunk, tokenizer)
        logging.info(f"  块 {i+1}: {chunk_tokens} tokens")
    
    return chunks

def _calculate_summary_tokens(repository_name, summary_dir):
    """
    为总结文件计算Token数量
    
    Args:
        repository_name: 信息库名称
        summary_dir: 总结文件目录
    """
    try:
        logging.info(f"开始为总结文件计算Token: {repository_name}")
        
        # 获取信息库目录
        repository_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                     'data', 'crawled_data', repository_name)
        
        # 创建token_count目录
        token_count_dir = os.path.join(repository_dir, 'token_count')
        os.makedirs(token_count_dir, exist_ok=True)
        
        # 获取所有总结文件
        summary_files = file_utils.list_files(summary_dir, ['.txt'])
        
        # 过滤掉不需要的文件
        filtered_files = []
        for file_path in summary_files:
            file_name = os.path.basename(file_path)
            if file_name in ['all_summaries.txt', 'content_hashes.json'] or \
               file_name.startswith('token_count_'):
                continue
            if '_summarized.txt' in file_name or file_name.endswith('_summary.txt'):
                filtered_files.append(file_path)
        
        if not filtered_files:
            logging.warning(f"没有找到总结文件: {summary_dir}")
            return
        
        # 为多种模型准备tokenizer
        tokenizers = {
            'token_count_gpt4o': token_utils.get_tokenizer('openai'),
            'token_count_deepseek': token_utils.get_tokenizer('deepseek'),
            'token_count_jina': token_utils.get_tokenizer('jina'),
        }
        
        token_counts = {k: 0 for k in tokenizers}
        token_tracker_paths = {
            k: os.path.join(token_count_dir, f"{k}.txt") for k in tokenizers
        }
        
        # 清空现有的Token文件
        for path in token_tracker_paths.values():
            if os.path.exists(path):
                os.remove(path)
        
        # 处理每个文件
        for file_path in filtered_files:
            try:
                content = file_utils.read_file(file_path)
                file_name = os.path.basename(file_path)
                
                for key, tokenizer in tokenizers.items():
                    tokens = token_utils.count_tokens(content, tokenizer)
                    token_counts[key] += tokens
                    # 写入每个文件的统计结果
                    with open(token_tracker_paths[key], 'a', encoding='utf-8') as f:
                        f.write(f"{file_name}: {tokens}\n")
                
                logging.info(f"计算Token完成: {file_name}")
                
            except Exception as e:
                logging.error(f"处理总结文件失败: {file_path}, 错误: {str(e)}")
        
        # 写入最终统计结果
        for key, count in token_counts.items():
            with open(token_tracker_paths[key], 'a', encoding='utf-8') as f:
                f.write(f"总Token数: {count}\n")
        
        logging.info(f"总结文件Token计算完成，总Token数: {sum(token_counts.values())}")
        
    except Exception as e:
        logging.error(f"计算总结文件Token失败: {str(e)}")

def _generate_qa_pairs_for_chunk(chunk_content, llm_config=None, repository_name=None):
    """
    为单个内容块生成问答对
    
    Args:
        chunk_content: 内容块
        llm_config: LLM配置（可选）
        repository_name: 信息库名称（可选）
        
    Returns:
        qa_pairs: 生成的问答对列表，格式为 [{"q": "问题", "a": "答案"}, ...]
    """
    try:
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
        
        if not api_key:
            raise ValueError(f"未设置{provider}的API密钥")
        
        # 获取API基础URL
        api_base_urls = {
            'openai': 'https://api.openai.com/v1/chat/completions',
            'qwen': 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions',
            'deepseek': 'https://api.deepseek.com/v1/chat/completions'
        }
        api_base_url = api_base_urls.get(provider, api_base_urls['openai'])
        
        # 获取提示词
        # 如果提供了信息库名称，获取信息库级别的Prompt配置
        if repository_name:
            try:
                from ..repository import repository_manager
                repo_prompt_config = repository_manager.get_merged_prompt_config(repository_name, merged_config)
                # 使用信息库级别的Prompt配置
                qa_stages = repo_prompt_config.get('qa_stages', {})
                chunk_config = qa_stages.get('chunk', {})
                qa_prompt = chunk_config.get('prompt', '''请根据以下内容生成5-10个高质量的问答对。
要求：
1. 问题应该清晰、具体、有价值
2. 答案应该准确、完整、基于给定内容
3. 避免过于简单或重复的问题
4. 输出格式为JSON数组，每个元素包含"q"（问题）和"a"（答案）字段

内容：''')
                qa_system_prompt = chunk_config.get('system_prompt', '你是一个专业的问答对生成助手，擅长从文本中提取关键信息并生成有价值的问答对。')
            except Exception as e:
                logging.warning(f"获取信息库Prompt配置失败，使用全局配置: {str(e)}")
                # 使用全局配置
                processor_config = merged_config.get('processor', {})
                qa_stages = processor_config.get('qa_stages', {})
                chunk_config = qa_stages.get('chunk', {})
                qa_prompt = chunk_config.get('prompt', '''请根据以下内容生成5-10个高质量的问答对。
要求：
1. 问题应该清晰、具体、有价值
2. 答案应该准确、完整、基于给定内容
3. 避免过于简单或重复的问题
4. 输出格式为JSON数组，每个元素包含"q"（问题）和"a"（答案）字段

内容：''')
                qa_system_prompt = chunk_config.get('system_prompt', '你是一个专业的问答对生成助手，擅长从文本中提取关键信息并生成有价值的问答对。')
        else:
            # 使用全局配置
            processor_config = merged_config.get('processor', {})
            qa_stages = processor_config.get('qa_stages', {})
            chunk_config = qa_stages.get('chunk', {})
            qa_prompt = chunk_config.get('prompt', '''请根据以下内容生成5-10个高质量的问答对。
要求：
1. 问题应该清晰、具体、有价值
2. 答案应该准确、完整、基于给定内容
3. 避免过于简单或重复的问题
4. 输出格式为JSON数组，每个元素包含"q"（问题）和"a"（答案）字段

内容：''')
            qa_system_prompt = chunk_config.get('system_prompt', '你是一个专业的问答对生成助手，擅长从文本中提取关键信息并生成有价值的问答对。')
        
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
                {'role': 'user', 'content': f"{qa_prompt}\n\n{chunk_content}"}
            ],
            'temperature': merged_config.get('temperature', 0.7),
            'max_tokens': merged_config.get('max_tokens', 2000)
        }
        
        # 发送请求
        response = requests.post(api_base_url, headers=headers, json=data, timeout=900)
        
        # 检查响应
        if response.status_code != 200:
            error_msg = f"API请求失败: {response.status_code} {response.text}"
            logging.error(error_msg)
            raise Exception(error_msg)
        
        # 解析响应
        response_data = response.json()
        
        # 提取问答对
        qa_text = response_data['choices'][0]['message']['content']
        
        # 解析JSON格式的问答对
        try:
            # 首先尝试清理文本，移除代码块标记
            cleaned_text = qa_text.strip()
            
            # 移除```json和```标记
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith('```'):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            
            cleaned_text = cleaned_text.strip()
            
            # 尝试直接解析为JSON数组
            try:
                qa_pairs = json.loads(cleaned_text)
                if not isinstance(qa_pairs, list):
                    qa_pairs = [qa_pairs]
            except json.JSONDecodeError:
                # 如果不是有效的JSON数组，尝试解析多个JSON对象
                qa_pairs = []
                
                # 按行分割，查找JSON对象
                lines = cleaned_text.split('\n')
                current_json = ""
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 如果行以{开始，开始新的JSON对象
                    if line.startswith('{'):
                        if current_json:
                            # 尝试解析之前的JSON对象
                            try:
                                qa_obj = json.loads(current_json)
                                if isinstance(qa_obj, dict):
                                    qa_pairs.append(qa_obj)
                            except:
                                pass
                        current_json = line
                    else:
                        # 继续当前JSON对象
                        current_json += line
                
                # 处理最后一个JSON对象
                if current_json:
                    try:
                        qa_obj = json.loads(current_json)
                        if isinstance(qa_obj, dict):
                            qa_pairs.append(qa_obj)
                    except:
                        pass
                
                # 如果还是没有找到，尝试正则表达式提取
                if not qa_pairs:
                    import re
                    # 查找所有JSON对象
                    json_objects = re.findall(r'\{[^{}]*"q"[^{}]*"a"[^{}]*\}', cleaned_text, re.DOTALL)
                    for json_str in json_objects:
                        try:
                            qa_obj = json.loads(json_str)
                            if isinstance(qa_obj, dict):
                                qa_pairs.append(qa_obj)
                        except:
                            continue
                
                # 最后尝试查找JSON数组
                if not qa_pairs:
                    json_match = re.search(r'\[.*\]', cleaned_text, re.DOTALL)
                    if json_match:
                        try:
                            qa_pairs = json.loads(json_match.group(0))
                        except:
                            logging.error(f"无法解析问答对JSON: {qa_text}")
                            return []
                    else:
                        logging.error(f"未找到JSON格式的问答对: {qa_text}")
                        return []
        
        except Exception as e:
            logging.error(f"解析问答对时发生错误: {str(e)}, 原文本: {qa_text}")
            return []
        
        # 验证和规范化格式
        valid_qa_pairs = []
        for qa in qa_pairs:
            if isinstance(qa, dict):
                # 兼容不同的字段名
                question = qa.get('q') or qa.get('question', '')
                answer = qa.get('a') or qa.get('answer', '')
                if question and answer:
                    valid_qa_pairs.append({
                        'q': question.strip(),
                        'a': answer.strip()
                    })
        
        logging.info(f"成功解析 {len(valid_qa_pairs)} 个问答对")
        return valid_qa_pairs
    
    except Exception as e:
        logging.error(f"生成问答对失败: {str(e)}")
        return []

def _reduce_qa_pairs_llm(qa_pairs, llm_config=None, repository_name=None):
    """
    使用LLM去重和筛选问答对
    
    Args:
        qa_pairs: 问答对列表
        llm_config: LLM配置（可选）
        repository_name: 信息库名称（可选）
        
    Returns:
        reduced_pairs: 去重后的问答对列表
    """
    try:
        if not qa_pairs:
            return []
        
        # 合并LLM配置
        merged_config = config.copy()
        if llm_config:
            merged_config.update(llm_config)
        
        # 获取LLM配置
        provider = merged_config.get('provider', 'openai')
        provider_config = merged_config.get(provider, {})
        api_key = provider_config.get('api_key', merged_config.get('api_key', ''))
        model = provider_config.get('model', merged_config.get('model', 'gpt-3.5-turbo'))
        
        if not api_key:
            raise ValueError(f"未设置{provider}的API密钥")
        
        # 获取API基础URL
        api_base_urls = {
            'openai': 'https://api.openai.com/v1/chat/completions',
            'qwen': 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions',
            'deepseek': 'https://api.deepseek.com/v1/chat/completions'
        }
        api_base_url = api_base_urls.get(provider, api_base_urls['openai'])
        
        # 获取提示词
        # 如果提供了信息库名称，获取信息库级别的Prompt配置
        if repository_name:
            try:
                from ..repository import repository_manager
                repo_prompt_config = repository_manager.get_merged_prompt_config(repository_name, merged_config)
                # 使用信息库级别的Prompt配置
                qa_stages = repo_prompt_config.get('qa_stages', {})
                reduce_config = qa_stages.get('reduce', {})
                reduce_prompt = reduce_config.get('prompt', '''请对以下问答对进行去重和筛选，保留最有价值、最独特的问答对。
要求：
1. 去除重复或高度相似的问题
2. 保留信息量大、有深度的问答对
3. 确保问题和答案的准确性
4. 输出格式与输入相同的JSON数组

问答对列表：''')
                reduce_system_prompt = reduce_config.get('system_prompt', '你是一个专业的内容审核助手，擅长识别重复或低质量的问答对，并保留最有价值的内容。')
            except Exception as e:
                logging.warning(f"获取信息库Prompt配置失败，使用全局配置: {str(e)}")
                # 从全局配置获取提示词
                processor_config = merged_config.get('processor', {})
                qa_stages = processor_config.get('qa_stages', {})
                reduce_config = qa_stages.get('reduce', {})
                reduce_prompt = reduce_config.get('prompt', '''请对以下问答对进行去重和筛选，保留最有价值、最独特的问答对。
要求：
1. 去除重复或高度相似的问题
2. 保留信息量大、有深度的问答对
3. 确保问题和答案的准确性
4. 输出格式与输入相同的JSON数组

问答对列表：''')
                reduce_system_prompt = reduce_config.get('system_prompt', '你是一个专业的内容审核助手，擅长识别重复或低质量的问答对，并保留最有价值的内容。')
        else:
            # 从全局配置获取提示词
            processor_config = merged_config.get('processor', {})
            qa_stages = processor_config.get('qa_stages', {})
            reduce_config = qa_stages.get('reduce', {})
            reduce_prompt = reduce_config.get('prompt', '''请对以下问答对进行去重和筛选，保留最有价值、最独特的问答对。
要求：
1. 去除重复或高度相似的问题
2. 保留信息量大、有深度的问答对
3. 确保问题和答案的准确性
4. 输出格式与输入相同的JSON数组

问答对列表：''')
            reduce_system_prompt = reduce_config.get('system_prompt', '你是一个专业的内容审核助手，擅长识别重复或低质量的问答对，并保留最有价值的内容。')
        
        # 准备请求数据
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        if provider == 'qwen':
            headers['X-DashScope-SSE'] = 'disable'
        
        # 将问答对转换为JSON字符串
        qa_json = json.dumps(qa_pairs, ensure_ascii=False, indent=2)
        
        data = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': reduce_system_prompt},
                {'role': 'user', 'content': f"{reduce_prompt}\n\n{qa_json}"}
            ],
            'temperature': 0.2,
            'max_tokens': merged_config.get('max_tokens', 3000)
        }
        
        # 发送请求
        response = requests.post(api_base_url, headers=headers, json=data, timeout=900)
        
        # 检查响应
        if response.status_code != 200:
            logging.error(f"Reduce API请求失败: {response.status_code}")
            return qa_pairs  # 失败时返回原始数据
        
        # 解析响应
        response_data = response.json()
        reduced_text = response_data['choices'][0]['message']['content']
        
        # 解析JSON
        try:
            # 清理文本，移除代码块标记
            cleaned_text = reduced_text.strip()
            
            # 移除```json和```标记
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith('```'):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            
            cleaned_text = cleaned_text.strip()
            
            # 尝试解析JSON
            reduced_pairs = json.loads(cleaned_text)
            if not isinstance(reduced_pairs, list):
                return qa_pairs
        except json.JSONDecodeError:
            # 尝试提取JSON部分
            import re
            json_match = re.search(r'\[.*\]', cleaned_text, re.DOTALL)
            if json_match:
                try:
                    reduced_pairs = json.loads(json_match.group(0))
                except:
                    return qa_pairs
            else:
                return qa_pairs
        
        # 验证格式
        valid_reduced_pairs = []
        for qa in reduced_pairs:
            if isinstance(qa, dict) and 'q' in qa and 'a' in qa:
                valid_reduced_pairs.append({
                    'q': qa['q'].strip(),
                    'a': qa['a'].strip()
                })
        
        return valid_reduced_pairs if valid_reduced_pairs else qa_pairs
    
    except Exception as e:
        logging.error(f"去重问答对失败: {str(e)}")
        return qa_pairs

def _evaluate_qa_pairs_llm(qa_pairs, llm_config=None, repository_name=None):
    """
    使用LLM评估问答对质量
    
    Args:
        qa_pairs: 问答对列表
        llm_config: LLM配置（可选）
        repository_name: 信息库名称（可选）
        
    Returns:
        evaluated_pairs: 评估后的问答对列表，包含self_eval字段
    """
    try:
        if not qa_pairs:
            return []
        
        # 合并LLM配置
        merged_config = config.copy()
        if llm_config:
            merged_config.update(llm_config)
        
        # 获取LLM配置
        provider = merged_config.get('provider', 'openai')
        provider_config = merged_config.get(provider, {})
        api_key = provider_config.get('api_key', merged_config.get('api_key', ''))
        model = provider_config.get('model', merged_config.get('model', 'gpt-3.5-turbo'))
        
        if not api_key:
            raise ValueError(f"未设置{provider}的API密钥")
        
        # 获取API基础URL
        api_base_urls = {
            'openai': 'https://api.openai.com/v1/chat/completions',
            'qwen': 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions',
            'deepseek': 'https://api.deepseek.com/v1/chat/completions'
        }
        api_base_url = api_base_urls.get(provider, api_base_urls['openai'])
        
        # 获取提示词
        # 如果提供了信息库名称，获取信息库级别的Prompt配置
        if repository_name:
            try:
                from ..repository import repository_manager
                repo_prompt_config = repository_manager.get_merged_prompt_config(repository_name, merged_config)
                # 使用信息库级别的Prompt配置
                qa_stages = repo_prompt_config.get('qa_stages', {})
                evaluate_config = qa_stages.get('evaluate', {})
                evaluate_prompt = evaluate_config.get('prompt', '''请对以下问答对进行质量评估。
要求：
1. 为每个问答对添加"self_eval"字段，评分范围1-5分
2. 5分：问题清晰具体，答案准确完整，信息价值高
3. 4分：问题较好，答案基本准确，有一定价值
4. 3分：问题和答案一般，基本可用
5. 2分：问题或答案有明显问题，价值较低
6. 1分：问题不清楚或答案错误，应该删除
7. 输出格式为JSON数组，保留原有的q和a字段，添加self_eval字段

问答对列表：''')
                evaluate_system_prompt = evaluate_config.get('system_prompt', '你是一个专业的内容评估助手，擅长评估问答对的质量和价值。')
            except Exception as e:
                logging.warning(f"获取信息库Prompt配置失败，使用全局配置: {str(e)}")
                # 从全局配置获取提示词
                processor_config = merged_config.get('processor', {})
                qa_stages = processor_config.get('qa_stages', {})
                evaluate_config = qa_stages.get('evaluate', {})
                evaluate_prompt = evaluate_config.get('prompt', '''请对以下问答对进行质量评估。
要求：
1. 为每个问答对添加"self_eval"字段，评分范围1-5分
2. 5分：问题清晰具体，答案准确完整，信息价值高
3. 4分：问题较好，答案基本准确，有一定价值
4. 3分：问题和答案一般，基本可用
5. 2分：问题或答案有明显问题，价值较低
6. 1分：问题不清楚或答案错误，应该删除
7. 输出格式为JSON数组，保留原有的q和a字段，添加self_eval字段

问答对列表：''')
                evaluate_system_prompt = evaluate_config.get('system_prompt', '你是一个专业的内容评估助手，擅长评估问答对的质量和价值。')
        else:
            # 从全局配置获取提示词
            processor_config = merged_config.get('processor', {})
            qa_stages = processor_config.get('qa_stages', {})
            evaluate_config = qa_stages.get('evaluate', {})
            evaluate_prompt = evaluate_config.get('prompt', '''请对以下问答对进行质量评估。
要求：
1. 为每个问答对添加"self_eval"字段，评分范围1-5分
2. 5分：问题清晰具体，答案准确完整，信息价值高
3. 4分：问题较好，答案基本准确，有一定价值
4. 3分：问题和答案一般，基本可用
5. 2分：问题或答案有明显问题，价值较低
6. 1分：问题不清楚或答案错误，应该删除
7. 输出格式为JSON数组，保留原有的q和a字段，添加self_eval字段

问答对列表：''')
            evaluate_system_prompt = evaluate_config.get('system_prompt', '你是一个专业的内容评估助手，擅长评估问答对的质量和价值。')
        
        # 准备请求数据
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        if provider == 'qwen':
            headers['X-DashScope-SSE'] = 'disable'
        
        # 将问答对转换为JSON字符串
        qa_json = json.dumps(qa_pairs, ensure_ascii=False, indent=2)
        
        data = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': evaluate_system_prompt},
                {'role': 'user', 'content': f"{evaluate_prompt}\n\n{qa_json}"}
            ],
            'temperature': 0.2,
            'max_tokens': merged_config.get('max_tokens', 3000)
        }
        
        # 发送请求
        response = requests.post(api_base_url, headers=headers, json=data, timeout=900)
        
        # 检查响应
        if response.status_code != 200:
            logging.error(f"Evaluate API请求失败: {response.status_code}")
            return qa_pairs  # 失败时返回原始数据
        
        # 解析响应
        response_data = response.json()
        evaluated_text = response_data['choices'][0]['message']['content']
        
        # 解析JSON
        try:
            # 清理文本，移除代码块标记
            cleaned_text = evaluated_text.strip()
            
            # 移除```json和```标记
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith('```'):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            
            cleaned_text = cleaned_text.strip()
            
            # 尝试解析JSON
            evaluated_pairs = json.loads(cleaned_text)
            if not isinstance(evaluated_pairs, list):
                return qa_pairs
        except json.JSONDecodeError:
            # 尝试提取JSON部分
            import re
            json_match = re.search(r'\[.*\]', cleaned_text, re.DOTALL)
            if json_match:
                try:
                    evaluated_pairs = json.loads(json_match.group(0))
                except:
                    return qa_pairs
            else:
                return qa_pairs
        
        # 验证格式
        valid_evaluated_pairs = []
        for qa in evaluated_pairs:
            if isinstance(qa, dict) and 'q' in qa and 'a' in qa:
                eval_qa = {
                    'q': qa['q'].strip(),
                    'a': qa['a'].strip()
                }
                # 添加评分（如果有）
                if 'self_eval' in qa:
                    eval_qa['self_eval'] = qa['self_eval']
                valid_evaluated_pairs.append(eval_qa)
        
        return valid_evaluated_pairs if valid_evaluated_pairs else qa_pairs
    
    except Exception as e:
        logging.error(f"评估问答对失败: {str(e)}")
        return qa_pairs

def get_process_status(task_id):
    """
    获取预处理任务状态
    
    Args:
        task_id: 任务ID
        
    Returns:
        status: 任务状态
    """
    # 优先从任务管理器获取状态
    task = task_manager.get_task(task_id)
    if task:
        return {
            'status': task['status'],
            'progress': task.get('progress', 0),
            'error': task.get('error'),
            'result': task.get('result'),
            'created_at': task.get('created_at'),
            'updated_at': task.get('updated_at'),
            'metadata': task.get('metadata', {})
        }
    
    # 兼容旧的状态存储
    with process_lock:
        return process_status.get(task_id)
