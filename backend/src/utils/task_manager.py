#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
任务管理器

用于管理和跟踪系统中的各种异步任务
"""

import json
import os
import time
from datetime import datetime
from threading import Lock
from typing import Dict, List, Optional, Any

class TaskManager:
    """任务管理器"""
    
    def __init__(self, storage_path: str = None):
        """
        初始化任务管理器
        
        Args:
            storage_path: 任务状态存储路径
        """
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.lock = Lock()
        
        # 设置存储路径
        if storage_path:
            self.storage_path = storage_path
        else:
            # 默认存储在data目录下
            self.storage_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                'data',
                'task_states.json'
            )
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        
        # 加载已有的任务状态
        self._load_tasks()
    
    def _load_tasks(self):
        """从文件加载任务状态"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    self.tasks = json.load(f)
            except Exception as e:
                print(f"加载任务状态失败: {e}")
                self.tasks = {}
    
    def _save_tasks(self):
        """保存任务状态到文件"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存任务状态失败: {e}")
    
    def create_task(self, task_id: str, task_type: str, repository_name: str, 
                   metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        创建新任务
        
        Args:
            task_id: 任务ID
            task_type: 任务类型 (summary, qa, token, crawl)
            repository_name: 仓库名称
            metadata: 额外的元数据
            
        Returns:
            任务信息
        """
        with self.lock:
            task = {
                'id': task_id,
                'type': task_type,
                'repository_name': repository_name,
                'status': 'pending',
                'progress': 0,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'started_at': None,
                'completed_at': None,
                'error': None,
                'result': None,
                'metadata': metadata or {}
            }
            
            self.tasks[task_id] = task
            self._save_tasks()
            
            return task
    
    def update_task(self, task_id: str, status: str = None, progress: int = None,
                   error: str = None, result: Any = None, **kwargs) -> Optional[Dict[str, Any]]:
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 任务状态 (pending, running, completed, failed)
            progress: 进度 (0-100)
            error: 错误信息
            result: 任务结果
            **kwargs: 其他要更新的字段
            
        Returns:
            更新后的任务信息
        """
        with self.lock:
            if task_id not in self.tasks:
                return None
            
            task = self.tasks[task_id]
            
            if status:
                task['status'] = status
                if status == 'running' and not task['started_at']:
                    task['started_at'] = datetime.now().isoformat()
                elif status in ['completed', 'failed']:
                    task['completed_at'] = datetime.now().isoformat()
            
            if progress is not None:
                task['progress'] = progress
            
            if error is not None:
                task['error'] = error
            
            if result is not None:
                task['result'] = result
            
            # 更新其他字段
            for key, value in kwargs.items():
                if key in task:
                    task[key] = value
            
            task['updated_at'] = datetime.now().isoformat()
            
            self._save_tasks()
            
            return task
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务信息
        """
        with self.lock:
            return self.tasks.get(task_id)
    
    def get_repository_tasks(self, repository_name: str, task_type: str = None,
                           status: str = None) -> List[Dict[str, Any]]:
        """
        获取仓库的任务列表
        
        Args:
            repository_name: 仓库名称
            task_type: 任务类型过滤
            status: 状态过滤
            
        Returns:
            任务列表
        """
        with self.lock:
            tasks = []
            for task in self.tasks.values():
                if task['repository_name'] == repository_name:
                    if task_type and task['type'] != task_type:
                        continue
                    if status and task['status'] != status:
                        continue
                    tasks.append(task)
            
            # 按创建时间倒序排序
            tasks.sort(key=lambda x: x['created_at'], reverse=True)
            
            return tasks
    
    def get_running_tasks(self, repository_name: str = None) -> List[Dict[str, Any]]:
        """
        获取运行中的任务
        
        Args:
            repository_name: 仓库名称（可选）
            
        Returns:
            运行中的任务列表
        """
        with self.lock:
            tasks = []
            for task in self.tasks.values():
                if task['status'] in ['pending', 'running']:
                    if repository_name and task['repository_name'] != repository_name:
                        continue
                    tasks.append(task)
            
            return tasks
    
    def clean_old_tasks(self, days: int = 7):
        """
        清理旧任务
        
        Args:
            days: 保留最近几天的任务
        """
        with self.lock:
            current_time = time.time()
            cutoff_time = current_time - (days * 24 * 60 * 60)
            
            tasks_to_remove = []
            for task_id, task in self.tasks.items():
                # 只清理已完成或失败的任务
                if task['status'] in ['completed', 'failed']:
                    created_time = datetime.fromisoformat(task['created_at']).timestamp()
                    if created_time < cutoff_time:
                        tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.tasks[task_id]
            
            if tasks_to_remove:
                self._save_tasks()
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功
        """
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task['status'] in ['pending', 'running']:
                    task['status'] = 'cancelled'
                    task['completed_at'] = datetime.now().isoformat()
                    self._save_tasks()
                    return True
            
            return False

# 全局任务管理器实例
task_manager = TaskManager() 