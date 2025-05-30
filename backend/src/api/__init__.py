#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API 蓝图模块

本模块定义了 TrueSight 的 RESTful API 接口。
"""

import os
import logging
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename

# 导入其他模块
from ..crawler import crawler_manager
from ..processor import processor_manager
from ..repository import repository_manager
from ..ragflow import ragflow_manager
from ..scheduler import scheduler_manager
from ..utils import file_utils
from . import error_logs

# 创建蓝图
api_blueprint = Blueprint('api', __name__)

# API 路由

# 健康检查
@api_blueprint.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'ok',
        'version': '1.0.0',
        'service': 'TrueSight'
    })

# 错误日志相关接口
@api_blueprint.route('/error_logs', methods=['GET'])
def get_error_logs():
    """获取错误日志列表"""
    try:
        logs = error_logs.get_error_logs()
        return jsonify({
            'success': True,
            'logs': logs
        })
    except Exception as e:
        logging.error(f"获取错误日志列表失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/error_logs/<log_id>', methods=['DELETE'])
def clear_error_log(log_id):
    """清除指定错误日志"""
    try:
        success = error_logs.clear_error_log(log_id)
        if not success:
            return jsonify({'success': False, 'error': '清除错误日志失败'}), 400
        return jsonify({
            'success': True
        })
    except Exception as e:
        logging.error(f"清除错误日志失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 爬虫相关接口

@api_blueprint.route('/crawler/start', methods=['POST'])
def start_crawl():
    """开始爬取任务"""
    try:
        data = request.json
        urls = data.get('urls')
        repository_name = data.get('repository_name')
        max_depth = data.get('max_depth')
        max_threads = data.get('max_threads')
        incremental = data.get('incremental', False)
        
        # 验证参数
        if not urls:
            return jsonify({'success': False, 'error': '缺少 URLs 参数'}), 400
        
        if not repository_name:
            return jsonify({'success': False, 'error': '缺少信息库名称参数'}), 400
        
        # 检查信息库是否存在，不存在则创建
        repository = repository_manager.get_repository(repository_name)
        if not repository:
            repository = repository_manager.create_repository(
                name=repository_name,
                source='crawler',
                urls=urls
            )
        
        # 开始爬取任务
        task_id = crawler_manager.start_crawl(
            urls=urls,
            repository_name=repository_name,
            max_depth=max_depth,
            max_threads=max_threads,
            incremental=incremental
        )
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'repository_name': repository_name
        })
    
    except Exception as e:
        logging.error(f"开始爬取任务失败: {str(e)}")
        error_logs.add_error_log('crawler', str(e), repository_name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/crawler/status/<task_id>', methods=['GET'])
def get_crawl_status(task_id):
    """获取爬取任务状态"""
    try:
        status = crawler_manager.get_crawl_status(task_id)
        
        if status is None:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
        
        return jsonify({
            'success': True,
            'status': status
        })
    
    except Exception as e:
        logging.error(f"获取爬取任务状态失败: {str(e)}")
        error_logs.add_error_log('crawler', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/crawler/stop/<task_id>', methods=['POST'])
def stop_crawl(task_id):
    """停止爬取任务"""
    try:
        success = crawler_manager.stop_crawl(task_id)
        
        if not success:
            return jsonify({'success': False, 'error': '停止任务失败'}), 400
        
        return jsonify({
            'success': True,
            'task_id': task_id
        })
    
    except Exception as e:
        logging.error(f"停止爬取任务失败: {str(e)}")
        error_logs.add_error_log('crawler', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500

# 预处理相关接口

@api_blueprint.route('/processor/token/calculate', methods=['POST'])
def calculate_tokens():
    """计算 Token 数量"""
    try:
        # 兼容直接传递字符串或JSON对象
        data = request.get_json(silent=True)
        if isinstance(data, dict):
            repository_name = data.get('repository_name') or data.get('name')
        elif isinstance(data, str):
            repository_name = data
        else:
            repository_name = request.data.decode('utf-8').strip() if request.data else None
        
        # 验证参数
        if not repository_name:
            return jsonify({'success': False, 'error': '缺少信息库名称参数'}), 400
        
        # 检查信息库是否存在
        repository = repository_manager.get_repository(repository_name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {repository_name}"}), 404
        
        # 计算 Token 数量
        task_id, token_counts = processor_manager.start_token_calculation(repository_name)
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'repository_name': repository_name,
            'token_counts': token_counts
        })
    
    except Exception as e:
        logging.error(f"计算 Token 数量失败: {str(e)}")
        error_logs.add_error_log('processor', str(e), repository_name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/processor/summary/generate', methods=['POST'])
def generate_summary():
    """生成内容总结"""
    try:
        data = request.get_json(silent=True)
        llm_config = None
        if isinstance(data, dict):
            repository_name = data.get('repository_name') or data.get('name')
            llm_config = data.get('llm_config')
        elif isinstance(data, str):
            repository_name = data
        else:
            repository_name = request.data.decode('utf-8').strip() if request.data else None
        
        # 验证参数
        if not repository_name:
            return jsonify({'success': False, 'error': '缺少信息库名称参数'}), 400
        
        # 检查信息库是否存在
        repository = repository_manager.get_repository(repository_name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {repository_name}"}), 404
        
        # 生成内容总结
        task_id = processor_manager.start_summary_generation(repository_name, llm_config)
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'repository_name': repository_name
        })
    
    except Exception as e:
        logging.error(f"生成内容总结失败: {str(e)}")
        error_logs.add_error_log('processor', str(e), repository_name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/processor/qa/generate', methods=['POST'])
def generate_qa():
    """生成问答对"""
    try:
        data = request.get_json(silent=True)
        llm_config = None
        if isinstance(data, dict):
            repository_name = data.get('repository_name') or data.get('name')
            llm_config = data.get('llm_config')
        elif isinstance(data, str):
            repository_name = data
        else:
            repository_name = request.data.decode('utf-8').strip() if request.data else None
        
        # 验证参数
        if not repository_name:
            return jsonify({'success': False, 'error': '缺少信息库名称参数'}), 400
        
        # 检查信息库是否存在
        repository = repository_manager.get_repository(repository_name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {repository_name}"}), 404
        
        # 生成问答对
        task_id = processor_manager.start_qa_generation(repository_name, llm_config)
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'repository_name': repository_name
        })
    
    except Exception as e:
        logging.error(f"生成问答对失败: {str(e)}")
        error_logs.add_error_log('processor', str(e), repository_name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/processor/status/<task_id>', methods=['GET'])
def get_process_status(task_id):
    """获取预处理任务状态"""
    try:
        status = processor_manager.get_process_status(task_id)
        
        if status is None:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
        
        return jsonify({
            'success': True,
            'status': status
        })
    
    except Exception as e:
        logging.error(f"获取预处理任务状态失败: {str(e)}")
        error_logs.add_error_log('processor', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/processor/repository/<name>/tasks', methods=['GET'])
def get_repository_tasks(name):
    """获取仓库的任务列表"""
    try:
        from ..utils.task_manager import task_manager
        
        # 获取查询参数
        task_type = request.args.get('type')
        status = request.args.get('status')
        
        # 获取任务列表
        tasks = task_manager.get_repository_tasks(name, task_type, status)
        
        return jsonify({
            'success': True,
            'tasks': tasks
        })
    
    except Exception as e:
        logging.error(f"获取仓库任务列表失败: {str(e)}")
        error_logs.add_error_log('processor', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/processor/repository/<name>/running-tasks', methods=['GET'])
def get_repository_running_tasks(name):
    """获取仓库的运行中任务"""
    try:
        from ..utils.task_manager import task_manager
        
        # 获取运行中的任务
        tasks = task_manager.get_running_tasks(name)
        
        # 按任务类型分组
        running_tasks = {
            'summary': None,
            'qa': None,
            'token': None,
            'crawl': None
        }
        
        for task in tasks:
            task_type = task.get('type')
            if task_type in running_tasks:
                running_tasks[task_type] = task
        
        return jsonify({
            'success': True,
            'running_tasks': running_tasks
        })
    
    except Exception as e:
        logging.error(f"获取仓库运行中任务失败: {str(e)}")
        error_logs.add_error_log('processor', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/processor/task/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    """取消任务"""
    try:
        from ..utils.task_manager import task_manager
        
        # 从任务管理器获取任务信息
        task = task_manager.get_task(task_id)
        if not task:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
        
        # 检查任务状态
        if task['status'] not in ['pending', 'running']:
            return jsonify({'success': False, 'error': '任务已完成或已取消'}), 400
        
        # 取消任务
        success = task_manager.cancel_task(task_id)
        if success:
            return jsonify({
                'success': True,
                'message': '任务已取消'
            })
        else:
            return jsonify({'success': False, 'error': '取消任务失败'}), 500
    
    except Exception as e:
        logging.error(f"取消任务失败: {str(e)}")
        error_logs.add_error_log('processor', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/processor/repository/<name>/cancel-tasks', methods=['POST'])
def cancel_repository_tasks(name):
    """取消信息库的指定类型任务"""
    try:
        from ..utils.task_manager import task_manager
        
        # 获取任务类型
        task_type = request.json.get('task_type')
        if not task_type:
            return jsonify({'success': False, 'error': '未指定任务类型'}), 400
        
        # 获取信息库的所有任务
        tasks = task_manager.get_repository_tasks(name)
        
        # 取消指定类型的运行中任务
        cancelled_count = 0
        for task in tasks:
            if task['type'] == task_type and task['status'] in ['pending', 'running']:
                if task_manager.cancel_task(task['id']):
                    cancelled_count += 1
        
        return jsonify({
            'success': True,
            'cancelled_count': cancelled_count,
            'message': f'已取消 {cancelled_count} 个{task_type}任务'
        })
    
    except Exception as e:
        logging.error(f"取消信息库任务失败: {str(e)}")
        error_logs.add_error_log('processor', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/crawler/repository/<name>/start', methods=['POST'])
def start_repository_crawl(name):
    """开始信息库爬取（增量爬取）"""
    try:
        # 检查信息库是否存在
        repository = repository_manager.get_repository(name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {name}"}), 404
        
        # 检查是否是爬虫来源
        if repository.get('source') != 'crawler':
            return jsonify({'success': False, 'error': '只有爬虫来源的信息库才能进行爬取'}), 400
        
        # 获取爬取URL
        urls = repository.get('urls', [])
        if not urls:
            return jsonify({'success': False, 'error': '信息库没有配置爬取URL'}), 400
        
        # 获取请求参数
        data = request.json or {}
        max_depth = data.get('max_depth')
        max_threads = data.get('max_threads')
        
        # 如果请求中没有提供参数，使用信息库配置中的值
        if max_depth is None:
            max_depth = repository.get('max_depth')
        if max_threads is None:
            max_threads = repository.get('max_threads')
        
        # 开始增量爬取任务
        task_id = crawler_manager.start_crawl(
            urls=urls,
            repository_name=name,
            max_depth=max_depth,
            max_threads=max_threads,
            incremental=True  # 增量爬取
        )
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'repository_name': name
        })
    
    except Exception as e:
        logging.error(f"开始信息库爬取失败: {str(e)}")
        error_logs.add_error_log('crawler', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

# 信息库相关接口

@api_blueprint.route('/repository/list', methods=['GET'])
def list_repositories():
    """获取信息库列表"""
    try:
        repositories = repository_manager.get_all_repositories()
        
        return jsonify({
            'success': True,
            'repositories': repositories
        })
    
    except Exception as e:
        logging.error(f"获取信息库列表失败: {str(e)}")
        error_logs.add_error_log('repository', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/repository/create', methods=['POST'])
def create_repository():
    """创建信息库"""
    try:
        data = request.json
        name = data.get('name')
        source = data.get('source', 'crawler')
        urls = data.get('urls')
        config_override = data.get('config_override', {})
        
        # 处理爬取深度和线程数
        max_depth = data.get('max_depth')
        max_threads = data.get('max_threads')
        
        # 添加调试日志
        logging.info(f"创建信息库请求数据: {data}")
        logging.info(f"max_depth: {max_depth}, max_threads: {max_threads}")
        
        # 如果提供了这些参数，添加到 config_override 中
        if max_depth is not None:
            config_override['max_depth'] = max_depth
        if max_threads is not None:
            config_override['max_threads'] = max_threads
            
        logging.info(f"config_override: {config_override}")
        
        # 验证参数
        if not name:
            return jsonify({'success': False, 'error': '缺少信息库名称参数'}), 400
        
        # 检查信息库是否已存在
        existing_repository = repository_manager.get_repository(name)
        if existing_repository:
            return jsonify({'success': False, 'error': f"信息库已存在: {name}"}), 400
        
        # 创建信息库
        repository = repository_manager.create_repository(
            name=name,
            source=source,
            urls=urls,
            config_override=config_override
        )
        
        logging.info(f"创建的信息库配置: max_depth={repository.get('max_depth')}, max_threads={repository.get('max_threads')}")
        
        return jsonify({
            'success': True,
            'repository': repository,
            'repository_name': name  # 确保返回 repository_name
        })
    
    except Exception as e:
        logging.error(f"创建信息库失败: {str(e)}")
        error_logs.add_error_log('repository', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/repository/<name>', methods=['GET'])
def get_repository(name):
    """获取信息库"""
    try:
        repository = repository_manager.get_repository(name)
        
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {name}"}), 404
        
        return jsonify({
            'success': True,
            'repository': repository
        })
    
    except Exception as e:
        logging.error(f"获取信息库失败: {str(e)}")
        error_logs.add_error_log('repository', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/repository/<name>', methods=['PUT'])
def update_repository(name):
    """更新信息库"""
    try:
        data = request.json
        
        # 检查信息库是否存在
        repository = repository_manager.get_repository(name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {name}"}), 404
        
        # 更新信息库
        updated_repository = repository_manager.update_repository(name, data)
        
        return jsonify({
            'success': True,
            'repository': updated_repository
        })
    
    except Exception as e:
        logging.error(f"更新信息库失败: {str(e)}")
        error_logs.add_error_log('repository', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/repository/<name>', methods=['DELETE'])
def delete_repository(name):
    """删除信息库"""
    try:
        # 检查信息库是否存在
        repository = repository_manager.get_repository(name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {name}"}), 404
        
        # 删除信息库
        success = repository_manager.delete_repository(name)
        
        return jsonify({
            'success': success
        })
    
    except Exception as e:
        logging.error(f"删除信息库失败: {str(e)}")
        error_logs.add_error_log('repository', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/repository/<name>/files', methods=['GET'])
def get_repository_files(name):
    """获取信息库文件列表"""
    try:
        # 获取查询参数
        file_types = request.args.get('file_types')
        include_summarized = request.args.get('include_summarized', 'true').lower() == 'true'
        include_qa = request.args.get('include_qa', 'true').lower() == 'true'
        
        # 解析文件类型
        if file_types:
            file_types = file_types.split(',')
            file_types = [f".{ft.strip()}" for ft in file_types]
        
        # 检查信息库是否存在
        repository = repository_manager.get_repository(name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {name}"}), 404
        
        # 获取文件列表
        files = repository_manager.get_repository_files(
            name,
            file_types=file_types,
            include_summarized=include_summarized,
            include_qa=include_qa
        )
        
        return jsonify({
            'success': True,
            'files': files
        })
    
    except Exception as e:
        logging.error(f"获取信息库文件列表失败: {str(e)}")
        error_logs.add_error_log('repository', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/repository/<name>/summary_files', methods=['GET'])
def get_repository_summary_files(name):
    """获取信息库总结文件列表"""
    try:
        # 检查信息库是否存在
        repository = repository_manager.get_repository(name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {name}"}), 404
        
        # 获取总结文件列表
        files = repository_manager.get_repository_summary_files(name)
        
        return jsonify({
            'success': True,
            'files': files
        })
    
    except Exception as e:
        logging.error(f"获取信息库总结文件列表失败: {str(e)}")
        error_logs.add_error_log('repository', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/repository/<name>/qa_files', methods=['GET'])
def get_repository_qa_files(name):
    """获取信息库问答文件列表"""
    try:
        # 检查信息库是否存在
        repository = repository_manager.get_repository(name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {name}"}), 404
        
        # 获取问答文件列表
        files = repository_manager.get_repository_qa_files(name)
        
        return jsonify({
            'success': True,
            'files': files
        })
    
    except Exception as e:
        logging.error(f"获取信息库问答文件列表失败: {str(e)}")
        error_logs.add_error_log('repository', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/repository/<name>/file', methods=['GET'])
def get_repository_file(name):
    """获取信息库文件内容"""
    try:
        file_path = request.args.get('path')
        
        # 验证参数
        if not file_path:
            return jsonify({'success': False, 'error': '缺少文件路径参数'}), 400
        
        # 检查信息库是否存在
        repository = repository_manager.get_repository(name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {name}"}), 404
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': f"文件不存在: {file_path}"}), 404
        
        # 获取文件内容
        return send_file(file_path)
    
    except Exception as e:
        logging.error(f"获取信息库文件内容失败: {str(e)}")
        error_logs.add_error_log('repository', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/repository/<name>/auto_update', methods=['PUT'])
def set_repository_auto_update(name):
    """设置信息库自动更新"""
    try:
        data = request.json
        auto_update = data.get('auto_update', False)
        update_frequency = data.get('update_frequency')
        
        # 检查信息库是否存在
        repository = repository_manager.get_repository(name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {name}"}), 404
        
        # 设置自动更新
        updated_repository = repository_manager.set_auto_update(name, auto_update, update_frequency)
        
        return jsonify({
            'success': True,
            'repository': updated_repository
        })
    
    except Exception as e:
        logging.error(f"设置信息库自动更新失败: {str(e)}")
        error_logs.add_error_log('repository', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/repository/<name>/direct_import', methods=['PUT'])
def set_repository_direct_import(name):
    """设置信息库直接入库"""
    try:
        data = request.json
        direct_import = data.get('direct_import', False)
        
        # 检查信息库是否存在
        repository = repository_manager.get_repository(name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {name}"}), 404
        
        # 设置直接入库
        updated_repository = repository_manager.set_direct_import(name, direct_import)
        
        return jsonify({
            'success': True,
            'repository': updated_repository
        })
    
    except Exception as e:
        logging.error(f"设置信息库直接入库失败: {str(e)}")
        error_logs.add_error_log('repository', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/repository/<name>/file_type_chunk_mapping', methods=['GET'])
def get_repository_file_type_chunk_mapping(name):
    """获取信息库文件类型映射"""
    try:
        # 检查信息库是否存在
        repository = repository_manager.get_repository(name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {name}"}), 404
        
        # 获取文件类型映射
        mapping = repository_manager.get_file_type_chunk_mapping(name)
        
        return jsonify({
            'success': True,
            'mapping': mapping
        })
    
    except Exception as e:
        logging.error(f"获取信息库文件类型映射失败: {str(e)}")
        error_logs.add_error_log('repository', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/repository/<name>/file_type_chunk_mapping', methods=['PUT'])
def update_repository_file_type_chunk_mapping(name):
    """更新信息库文件类型映射"""
    try:
        data = request.json
        file_type = data.get('file_type')
        chunk_method = data.get('chunk_method')
        parser_config = data.get('parser_config')
        
        # 验证参数
        if not file_type or not chunk_method:
            return jsonify({'success': False, 'error': '缺少必要参数: file_type 和 chunk_method'}), 400
        
        # 检查信息库是否存在
        repository = repository_manager.get_repository(name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {name}"}), 404
        
        # 更新文件类型映射
        updated_repository = repository_manager.update_file_type_chunk_mapping(
            name, file_type, chunk_method, parser_config
        )
        
        return jsonify({
            'success': True,
            'repository': updated_repository
        })
    
    except Exception as e:
        logging.error(f"更新信息库文件类型映射失败: {str(e)}")
        error_logs.add_error_log('repository', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

# RAGFlow 相关接口

@api_blueprint.route('/ragflow/datasets', methods=['GET'])
def list_ragflow_datasets():
    """获取RAGFlow数据集列表"""
    try:
        datasets = ragflow_manager.list_datasets()
        
        return jsonify({
            'success': True,
            'datasets': datasets
        })
    
    except Exception as e:
        logging.error(f"获取RAGFlow数据集列表失败: {str(e)}")
        error_logs.add_error_log('ragflow', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/ragflow/import/<name>', methods=['POST'])
def import_repository_to_ragflow(name):
    """导入信息库到RAGFlow"""
    try:
        # 检查信息库是否存在
        repository = repository_manager.get_repository(name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {name}"}), 404
        
        # 导入信息库到RAGFlow
        success, message = ragflow_manager.import_repository(name)
        
        if not success:
            return jsonify({'success': False, 'error': message}), 400
        
        return jsonify({
            'success': True,
            'message': message
        })
    
    except Exception as e:
        logging.error(f"导入信息库到RAGFlow失败: {str(e)}")
        error_logs.add_error_log('ragflow', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/ragflow/sync/<name>', methods=['POST'])
def sync_repository_with_ragflow(name):
    """同步信息库到RAGFlow"""
    try:
        repository = repository_manager.get_repository(name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {name}"}), 404

        result = ragflow_manager.sync_repository(name, repository)

        return jsonify({
            'success': True,
            'result': result
        })

    except Exception as e:
        logging.error(f"同步信息库到RAGFlow失败: {str(e)}")
        error_logs.add_error_log('ragflow', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/ragflow/mapping/check', methods=['GET'])
def check_ragflow_mapping():
    """检查RAGFlow映射关系"""
    try:
        result = ragflow_manager.check_and_fix_mapping()
        
        return jsonify({
            'success': True,
            'result': result
        })
    
    except Exception as e:
        logging.error(f"检查RAGFlow映射关系失败: {str(e)}")
        error_logs.add_error_log('ragflow', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/ragflow/mapping/cleanup', methods=['POST'])
def cleanup_orphaned_ragflow_datasets():
    """清理孤儿RAGFlow Datasets"""
    try:
        data = request.json
        dataset_ids = data.get('dataset_ids', [])
        
        if not dataset_ids:
            return jsonify({'success': False, 'error': '缺少dataset_ids参数'}), 400
        
        result = ragflow_manager.cleanup_orphaned_datasets(dataset_ids)
        
        return jsonify({
            'success': result['success'],
            'result': result
        })
    
    except Exception as e:
        logging.error(f"清理孤儿RAGFlow Datasets失败: {str(e)}")
        error_logs.add_error_log('ragflow', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/ragflow/sync-status/<name>', methods=['GET'])
def get_repository_sync_status(name):
    """获取信息库文件同步状态"""
    try:
        repository = repository_manager.get_repository(name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {name}"}), 404
        
        sync_status = repository.get('file_sync_status', {})
        
        # 统计信息
        total_files = len(sync_status)
        synced_files = sum(1 for status in sync_status.values() if status.get('document_id'))
        
        return jsonify({
            'success': True,
            'data': {
                'repository_name': name,
                'total_files': total_files,
                'synced_files': synced_files,
                'sync_status': sync_status
            }
        })
        
    except Exception as e:
        logging.error(f"获取同步状态失败: {str(e)}")
        error_logs.add_error_log('ragflow', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/ragflow/sync-status/<name>/cleanup', methods=['POST'])
def cleanup_repository_sync_status(name):
    """清理信息库的同步状态"""
    try:
        cleaned_count = ragflow_manager.cleanup_sync_status(name)
        
        return jsonify({
            'success': True,
            'cleaned_count': cleaned_count,
            'message': f"清理了 {cleaned_count} 个过期的同步状态记录"
        })
        
    except Exception as e:
        logging.error(f"清理同步状态失败: {str(e)}")
        error_logs.add_error_log('ragflow', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/ragflow/sync-check/<name>', methods=['GET'])
def check_repository_ragflow_sync(name):
    """检查信息库与RAGFlow的同步状态"""
    try:
        # 检查信息库是否存在
        repository = repository_manager.get_repository(name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {name}"}), 404
        
        # 执行同步状态检查
        sync_status = ragflow_manager.check_repository_sync_status(name)
        
        return jsonify({
            'success': True,
            'sync_status': sync_status
        })
        
    except Exception as e:
        logging.error(f"检查RAGFlow同步状态失败: {str(e)}")
        error_logs.add_error_log('ragflow', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

# 配置相关接口

@api_blueprint.route('/config', methods=['GET'])
def get_config():
    """获取全局配置"""
    try:
        from ..utils.config_loader import get_config
        config = get_config()
        
        return jsonify({
            'success': True,
            'config': config
        })
    
    except Exception as e:
        logging.error(f"获取全局配置失败: {str(e)}")
        error_logs.add_error_log('system', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/config', methods=['PUT'])
def update_config():
    """更新全局配置"""
    try:
        data = request.json
        
        from ..utils.config_loader import update_config
        success = update_config(data)
        
        if not success:
            return jsonify({'success': False, 'error': '更新配置失败'}), 400
        
        # 检查是否更新了RAGFlow配置，如果是则重新加载RAGFlow管理器
        if 'ragflow' in data:
            try:
                from ..ragflow import ragflow_manager
                reload_success = ragflow_manager.reload()
                if reload_success:
                    logging.info("RAGFlow配置已更新，管理器重新加载成功")
                else:
                    logging.warning("RAGFlow配置已更新，但管理器重新加载失败")
            except Exception as e:
                logging.error(f"重新加载RAGFlow管理器时出错: {str(e)}")
        
        return jsonify({
            'success': True,
            'config': data
        })
    
    except Exception as e:
        logging.error(f"更新全局配置失败: {str(e)}")
        error_logs.add_error_log('system', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500
