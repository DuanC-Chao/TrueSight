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
from backend.src.crawler import crawler_manager
from backend.src.processor import processor_manager
from backend.src.repository import repository_manager
from backend.src.ragflow import ragflow_manager
from backend.src.scheduler import scheduler_manager
from backend.src.utils import file_utils
from backend.src.api import error_logs

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

@api_blueprint.route('/crawler/pause/<task_id>', methods=['POST'])
def pause_crawl(task_id):
    """暂停爬取任务"""
    try:
        success = crawler_manager.pause_crawl(task_id)
        
        if not success:
            return jsonify({'success': False, 'error': '暂停任务失败'}), 400
        
        return jsonify({
            'success': True,
            'task_id': task_id
        })
    
    except Exception as e:
        logging.error(f"暂停爬取任务失败: {str(e)}")
        error_logs.add_error_log('crawler', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/crawler/resume/<task_id>', methods=['POST'])
def resume_crawl(task_id):
    """恢复爬取任务"""
    try:
        success = crawler_manager.resume_crawl(task_id)
        
        if not success:
            return jsonify({'success': False, 'error': '恢复任务失败'}), 400
        
        return jsonify({
            'success': True,
            'task_id': task_id
        })
    
    except Exception as e:
        logging.error(f"恢复爬取任务失败: {str(e)}")
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
        config_override = data.get('config_override')
        
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
        
        return jsonify({
            'success': True,
            'repository': repository
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

# 配置相关接口

@api_blueprint.route('/config', methods=['GET'])
def get_config():
    """获取全局配置"""
    try:
        from backend.src.utils.config_loader import get_config
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
        
        from backend.src.utils.config_loader import update_config
        success = update_config(data)
        
        if not success:
            return jsonify({'success': False, 'error': '更新配置失败'}), 400
        
        return jsonify({
            'success': True,
            'config': data
        })
    
    except Exception as e:
        logging.error(f"更新全局配置失败: {str(e)}")
        error_logs.add_error_log('system', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500
