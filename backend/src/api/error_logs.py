#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
错误日志模块

本模块提供错误日志的存储、查询和管理功能。
"""

import os
import json
import time
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

# 错误日志存储路径
ERROR_LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                             'logs', 'error_logs')

# 确保目录存在
os.makedirs(ERROR_LOGS_DIR, exist_ok=True)

# 错误日志文件路径
ERROR_LOGS_FILE = os.path.join(ERROR_LOGS_DIR, 'error_logs.json')

# 初始化错误日志文件
if not os.path.exists(ERROR_LOGS_FILE):
    with open(ERROR_LOGS_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f)

def add_error_log(task_type: str, error_message: str, repository_name: Optional[str] = None, 
                 stack_trace: Optional[str] = None) -> str:
    """
    添加错误日志
    
    Args:
        task_type: 任务类型，如 'crawler', 'processor', 'ragflow', 'scheduler'
        error_message: 错误信息
        repository_name: 信息库名称，可选
        stack_trace: 堆栈跟踪，可选
        
    Returns:
        str: 错误日志ID
    """
    try:
        # 读取现有日志
        logs = []
        if os.path.exists(ERROR_LOGS_FILE):
            with open(ERROR_LOGS_FILE, 'r', encoding='utf-8') as f:
                try:
                    logs = json.load(f)
                except json.JSONDecodeError:
                    logs = []
        
        # 生成唯一ID
        log_id = str(uuid.uuid4())
        
        # 创建日志条目
        log_entry = {
            'id': log_id,
            'timestamp': datetime.now().isoformat(),
            'task_type': task_type,
            'repository_name': repository_name,
            'error_message': error_message,
            'stack_trace': stack_trace
        }
        
        # 添加到日志列表
        logs.append(log_entry)
        
        # 保存日志
        with open(ERROR_LOGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
        
        return log_id
    
    except Exception as e:
        logging.error(f"添加错误日志失败: {str(e)}")
        return ""

def get_error_logs() -> List[Dict[str, Any]]:
    """
    获取所有错误日志
    
    Returns:
        List[Dict[str, Any]]: 错误日志列表
    """
    try:
        if not os.path.exists(ERROR_LOGS_FILE):
            return []
        
        with open(ERROR_LOGS_FILE, 'r', encoding='utf-8') as f:
            try:
                logs = json.load(f)
                # 按时间戳降序排序
                logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                return logs
            except json.JSONDecodeError:
                return []
    
    except Exception as e:
        logging.error(f"获取错误日志失败: {str(e)}")
        return []

def get_error_log(log_id: str) -> Optional[Dict[str, Any]]:
    """
    获取指定ID的错误日志
    
    Args:
        log_id: 错误日志ID
        
    Returns:
        Optional[Dict[str, Any]]: 错误日志，如果不存在则返回None
    """
    try:
        logs = get_error_logs()
        for log in logs:
            if log.get('id') == log_id:
                return log
        return None
    
    except Exception as e:
        logging.error(f"获取错误日志失败: {str(e)}")
        return None

def clear_error_log(log_id: str) -> bool:
    """
    清除指定ID的错误日志
    
    Args:
        log_id: 错误日志ID
        
    Returns:
        bool: 是否成功清除
    """
    try:
        if not os.path.exists(ERROR_LOGS_FILE):
            return False
        
        with open(ERROR_LOGS_FILE, 'r', encoding='utf-8') as f:
            try:
                logs = json.load(f)
            except json.JSONDecodeError:
                return False
        
        # 过滤掉要删除的日志
        logs = [log for log in logs if log.get('id') != log_id]
        
        # 保存日志
        with open(ERROR_LOGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
        
        return True
    
    except Exception as e:
        logging.error(f"清除错误日志失败: {str(e)}")
        return False

def clear_all_error_logs() -> bool:
    """
    清除所有错误日志
    
    Returns:
        bool: 是否成功清除
    """
    try:
        # 保存空日志
        with open(ERROR_LOGS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
        
        return True
    
    except Exception as e:
        logging.error(f"清除所有错误日志失败: {str(e)}")
        return False
