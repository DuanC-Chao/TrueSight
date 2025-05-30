#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
调度管理器模块

本模块负责管理定时任务，包括自动更新信息库等功能。
"""

import os
import logging
import threading
import time
from datetime import datetime, timedelta
import pytz

# 导入其他模块
from ..crawler import crawler_manager
from ..processor import processor_manager
from ..repository import repository_manager
from ..ragflow import ragflow_manager

# 全局配置
config = {}
# 调度器线程
scheduler_thread = None
# 调度器运行标志
scheduler_running = False
# 任务队列
task_queue = []
# 任务锁
task_lock = threading.Lock()

def init(app_config):
    """
    初始化调度管理器
    
    Args:
        app_config: 应用配置
    """
    global config, scheduler_running, scheduler_thread
    
    # 合并应用配置
    if 'scheduler' in app_config:
        config.update(app_config['scheduler'])
    
    # 启动调度器线程
    scheduler_running = True
    scheduler_thread = threading.Thread(target=_scheduler_worker)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    logging.info("调度管理器初始化完成")

def _scheduler_worker():
    """调度器工作线程"""
    global scheduler_running
    
    logging.info("调度器线程启动")
    
    while scheduler_running:
        try:
            # 检查是否有需要执行的任务
            _check_scheduled_tasks()
            
            # 执行队列中的任务
            _execute_queued_tasks()
            
            # 休眠一段时间
            time.sleep(60)  # 每分钟检查一次
        
        except Exception as e:
            logging.error(f"调度器线程异常: {str(e)}")
            time.sleep(300)  # 出错后等待5分钟再重试

def _check_scheduled_tasks():
    """检查是否有需要执行的定时任务"""
    # 获取当前时间（北京时间）
    now = datetime.now(pytz.timezone('Asia/Shanghai'))
    
    # 获取所有信息库
    repositories = repository_manager.get_all_repositories()
    
    for repository in repositories:
        # 检查是否启用自动更新
        if repository.get('auto_update') and repository.get('update_frequency'):
            # 检查是否需要执行
            if _should_execute_task(repository, now):
                # 添加到任务队列
                _add_task_to_queue({
                    'type': 'auto_update',
                    'repository_name': repository['name'],
                    'scheduled_time': now.isoformat()
                })

def _should_execute_task(repository, now):
    """
    判断是否应该执行任务
    
    Args:
        repository: 信息库配置
        now: 当前时间
        
    Returns:
        bool: 是否应该执行
    """
    # 获取更新频率
    frequency = repository.get('update_frequency')
    
    # 检查是否是爬虫来源
    if repository.get('source') != 'crawler':
        return False
    
    # 检查是否有上次更新时间
    last_update_str = repository.get('last_auto_update')
    if not last_update_str:
        # 没有上次更新时间，应该执行
        return True
    
    try:
        # 解析上次更新时间
        last_update = datetime.fromisoformat(last_update_str)
        
        # 转换为北京时间
        if last_update.tzinfo is None:
            last_update = pytz.timezone('Asia/Shanghai').localize(last_update)
        
        # 根据频率判断是否应该执行
        if frequency == 'daily':
            # 每天 00:01 执行
            return (now.hour == 0 and now.minute >= 1 and 
                    (now.date() > last_update.date()))
        
        elif frequency == 'weekly':
            # 每周一 00:01 执行
            return (now.hour == 0 and now.minute >= 1 and 
                    now.weekday() == 0 and  # 0 表示周一
                    (now.date() - last_update.date()).days >= 7)
        
        elif frequency == 'monthly':
            # 每月第一天 00:01 执行
            return (now.hour == 0 and now.minute >= 1 and 
                    now.day == 1 and
                    (now.date().month != last_update.date().month or 
                     now.date().year != last_update.date().year))
        
        elif frequency == 'yearly':
            # 每年第一天 00:01 执行
            return (now.hour == 0 and now.minute >= 1 and 
                    now.day == 1 and now.month == 1 and
                    now.date().year > last_update.date().year)
        
        else:
            return False
    
    except Exception as e:
        logging.error(f"解析上次更新时间失败: {str(e)}")
        return True

def _add_task_to_queue(task):
    """
    添加任务到队列
    
    Args:
        task: 任务信息
    """
    global task_queue
    
    with task_lock:
        # 检查是否已有相同任务
        for existing_task in task_queue:
            if (existing_task['type'] == task['type'] and 
                existing_task['repository_name'] == task['repository_name']):
                return
        
        # 添加到队列
        task_queue.append(task)
        logging.info(f"添加任务到队列: {task['type']} - {task['repository_name']}")

def _execute_queued_tasks():
    """执行队列中的任务"""
    global task_queue
    
    with task_lock:
        if not task_queue:
            return
        
        # 获取第一个任务
        task = task_queue.pop(0)
    
    try:
        # 执行任务
        if task['type'] == 'auto_update':
            _execute_auto_update_task(task)
    
    except Exception as e:
        logging.error(f"执行任务失败: {task['type']} - {task['repository_name']}, 错误: {str(e)}")

def _execute_auto_update_task(task):
    """
    执行自动更新任务
    
    Args:
        task: 任务信息
    """
    repository_name = task['repository_name']
    
    logging.info(f"执行自动更新任务: {repository_name}")
    
    try:
        # 获取信息库配置
        repository = repository_manager.get_repository(repository_name)
        
        if not repository:
            logging.error(f"信息库不存在: {repository_name}")
            return
        
        # 检查是否是爬虫来源
        if repository.get('source') != 'crawler':
            logging.error(f"信息库不是爬虫来源: {repository_name}")
            return
        
        # 检查是否有URL
        urls = repository.get('urls')
        if not urls:
            logging.error(f"信息库没有URL: {repository_name}")
            return
        
        # 开始增量爬取
        task_id = crawler_manager.start_crawl(
            urls=urls,
            repository_name=repository_name,
            incremental=True
        )
        
        # 等待爬取完成
        while True:
            status = crawler_manager.get_crawl_status(task_id)
            if status['status'] in ['completed', 'failed', 'stopped']:
                break
            time.sleep(5)
        
        if status['status'] != 'completed':
            logging.error(f"爬取任务失败: {task_id}")
            return
        
        # 计算Token
        token_task_id, _ = processor_manager.start_token_calculation(repository_name)
        
        # 等待Token计算完成
        while True:
            status = processor_manager.get_process_status(token_task_id)
            if status['status'] in ['completed', 'failed']:
                break
            time.sleep(5)
        
        # 判断是否直接入库
        if repository.get('direct_import', False):
            # 直接同步到RAGFlow
            result = ragflow_manager.sync_repository_with_ragflow(repository_name, repository)
            
            if not result['success']:
                logging.error(f"同步到RAGFlow失败: {repository_name}, 错误: {result.get('error')}")
                return
        else:
            # 生成总结
            summary_task_id = processor_manager.start_summary_generation(repository_name)
            
            # 等待总结生成完成
            while True:
                status = processor_manager.get_process_status(summary_task_id)
                if status['status'] in ['completed', 'failed']:
                    break
                time.sleep(5)
            
            if status['status'] != 'completed':
                logging.error(f"总结生成任务失败: {summary_task_id}")
                return
            
            # 生成问答对
            qa_task_id = processor_manager.start_qa_generation(repository_name)
            
            # 等待问答对生成完成
            while True:
                status = processor_manager.get_process_status(qa_task_id)
                if status['status'] in ['completed', 'failed']:
                    break
                time.sleep(5)
            
            if status['status'] != 'completed':
                logging.error(f"问答对生成任务失败: {qa_task_id}")
                return
            
            # 同步到RAGFlow
            result = ragflow_manager.sync_repository_with_ragflow(repository_name, repository)
            
            if not result['success']:
                logging.error(f"同步到RAGFlow失败: {repository_name}, 错误: {result.get('error')}")
                return
        
        # 更新信息库状态
        repository_manager.update_repository_status(repository_name, 'complete')
        
        # 更新上次自动更新时间
        repository_manager.update_repository(repository_name, {
            'last_auto_update': datetime.now(pytz.timezone('Asia/Shanghai')).isoformat()
        })
        
        logging.info(f"自动更新任务完成: {repository_name}")
    
    except Exception as e:
        logging.error(f"自动更新任务异常: {repository_name}, 错误: {str(e)}")
        
        # 更新信息库状态
        try:
            repository_manager.update_repository_status(repository_name, 'error')
        except:
            pass

def add_auto_update_task(repository_name):
    """
    添加自动更新任务
    
    Args:
        repository_name: 信息库名称
        
    Returns:
        success: 是否成功
    """
    # 获取信息库配置
    repository = repository_manager.get_repository(repository_name)
    
    if not repository:
        return False
    
    # 检查是否是爬虫来源
    if repository.get('source') != 'crawler':
        return False
    
    # 检查是否启用自动更新
    if not repository.get('auto_update'):
        return False
    
    # 添加到任务队列
    _add_task_to_queue({
        'type': 'auto_update',
        'repository_name': repository_name,
        'scheduled_time': datetime.now(pytz.timezone('Asia/Shanghai')).isoformat()
    })
    
    return True

def shutdown():
    """关闭调度管理器"""
    global scheduler_running
    
    scheduler_running = False
    
    if scheduler_thread:
        scheduler_thread.join(timeout=5)
    
    logging.info("调度管理器已关闭")
