#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
日志设置模块

本模块负责配置日志系统，包括日志格式、级别和输出方式。
"""

import os
import logging
from logging.handlers import RotatingFileHandler
import datetime

def setup_logger(log_level='INFO', log_file=None):
    """
    设置日志系统
    
    Args:
        log_level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_file: 日志文件路径，如果为None则使用默认路径
    """
    # 设置日志级别
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    
    # 设置日志格式
    log_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(log_format, date_format)
    
    # 清除现有的处理器
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 设置根日志器级别
    root_logger.setLevel(numeric_level)
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 添加文件处理器（如果指定了日志文件）
    if log_file is None:
        # 使用默认日志文件路径
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # 使用日期作为文件名
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(log_dir, f'truesight_{today}.log')
    
    # 确保日志目录存在
    log_dir = os.path.dirname(log_file)
    os.makedirs(log_dir, exist_ok=True)
    
    # 创建轮转文件处理器（最大10MB，保留5个备份）
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # 设置第三方库的日志级别
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    
    logging.info(f"日志系统初始化完成，级别: {log_level}, 文件: {log_file}")

def get_error_logger():
    """
    获取错误日志记录器
    
    Returns:
        logger: 错误日志记录器
    """
    # 创建错误日志记录器
    error_logger = logging.getLogger('error')
    
    # 如果已经有处理器，则不重复添加
    if error_logger.handlers:
        return error_logger
    
    # 设置日志级别
    error_logger.setLevel(logging.ERROR)
    
    # 设置日志格式
    log_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(log_format, date_format)
    
    # 创建错误日志文件
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    error_log_file = os.path.join(log_dir, 'error.log')
    
    # 创建轮转文件处理器（最大10MB，保留10个备份）
    file_handler = RotatingFileHandler(
        error_log_file, maxBytes=10*1024*1024, backupCount=10, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    error_logger.addHandler(file_handler)
    
    return error_logger

def log_error(message, repository_name=None, task_type=None):
    """
    记录错误日志
    
    Args:
        message: 错误信息
        repository_name: 信息库名称
        task_type: 任务类型
    """
    error_logger = get_error_logger()
    
    # 构建错误日志
    log_message = message
    if repository_name:
        log_message = f"[{repository_name}] {log_message}"
    if task_type:
        log_message = f"[{task_type}] {log_message}"
    
    # 记录错误
    error_logger.error(log_message)
