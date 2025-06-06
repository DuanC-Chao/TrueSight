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
from datetime import datetime

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
        use_summary_files = None
        
        if isinstance(data, dict):
            repository_name = data.get('repository_name') or data.get('name')
            llm_config = data.get('llm_config')
            use_summary_files = data.get('use_summary_files')  # True=基于总结，False=基于原始文件，None=自动判断
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
        
        # 如果指定使用总结文件，检查总结是否存在
        if use_summary_files is True:
            summary_files = repository_manager.get_repository_summary_files(repository_name)
            if not summary_files:
                return jsonify({'success': False, 'error': '未找到总结文件，请先生成总结'}), 400
        
        # 生成问答对
        task_id = processor_manager.start_qa_generation(repository_name, llm_config, use_summary_files)
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'repository_name': repository_name,
            'use_summary_files': use_summary_files
        })
    
    except Exception as e:
        logging.error(f"生成问答对失败: {str(e)}")
        error_logs.add_error_log('processor', str(e), repository_name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/processor/qa/generate_from_original', methods=['POST'])
def generate_qa_from_original():
    """基于原始文件生成问答对"""
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
        
        # 强制使用原始文件生成问答对
        task_id = processor_manager.start_qa_generation(repository_name, llm_config, use_summary_files=False)
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'repository_name': repository_name,
            'use_summary_files': False
        })
    
    except Exception as e:
        logging.error(f"基于原始文件生成问答对失败: {str(e)}")
        error_logs.add_error_log('processor', str(e), repository_name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/processor/qa/generate_from_summary', methods=['POST'])
def generate_qa_from_summary():
    """基于总结文件生成问答对"""
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
        
        # 检查总结文件是否存在
        summary_files = repository_manager.get_repository_summary_files(repository_name)
        if not summary_files:
            return jsonify({'success': False, 'error': '未找到总结文件，请先生成总结'}), 400
        
        # 强制使用总结文件生成问答对
        task_id = processor_manager.start_qa_generation(repository_name, llm_config, use_summary_files=True)
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'repository_name': repository_name,
            'use_summary_files': True
        })
    
    except Exception as e:
        logging.error(f"基于总结文件生成问答对失败: {str(e)}")
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
        # 检查是否是文件上传请求
        if request.content_type and 'multipart/form-data' in request.content_type:
            # 处理文件上传
            name = request.form.get('name')
            description = request.form.get('description', '')
            source = request.form.get('source', 'upload')
            
            # 增强的调试日志
            logging.info(f"接收到文件上传请求: name={name}, source={source}")
            logging.info(f"request.content_type: {request.content_type}")
            logging.info(f"request.form: {dict(request.form)}")
            logging.info(f"request.files keys: {list(request.files.keys())}")
            
            # 验证参数
            if not name:
                return jsonify({'success': False, 'error': '缺少信息库名称参数'}), 400
            
            # 检查信息库是否已存在
            existing_repository = repository_manager.get_repository(name)
            if existing_repository:
                return jsonify({'success': False, 'error': f"信息库已存在: {name}"}), 400
            
            # 增强的文件获取逻辑，更好地处理跨平台差异
            uploaded_files = []
            
            # 尝试多种可能的字段名，处理不同前端框架和浏览器的差异
            possible_field_names = ['files', 'files[]', 'file', 'upload', 'document']
            for field_name in possible_field_names:
                files = request.files.getlist(field_name)
                if files and any(f.filename for f in files):  # 确保文件有有效的文件名
                    uploaded_files.extend(files)
                    logging.info(f"从字段 '{field_name}' 获取到 {len(files)} 个文件")
            
            # 如果还是没有文件，遍历所有文件字段
            if not uploaded_files:
                for key in request.files.keys():
                    files = request.files.getlist(key)
                    valid_files = [f for f in files if f.filename and f.filename.strip()]
                    if valid_files:
                        uploaded_files.extend(valid_files)
                        logging.info(f"从字段 '{key}' 获取到 {len(valid_files)} 个有效文件")
            
            logging.info(f"总共获取到的文件数量: {len(uploaded_files)}")
            for i, file in enumerate(uploaded_files):
                file_size = 0
                try:
                    # 尝试获取文件大小
                    file.seek(0, 2)  # 移动到文件末尾
                    file_size = file.tell()
                    file.seek(0)  # 重置到文件开头
                except:
                    file_size = 0
                
                logging.info(f"文件 {i}: filename={file.filename}, content_type={getattr(file, 'content_type', getattr(file, 'mimetype', 'unknown'))}, size={file_size}")
            
            if not uploaded_files:
                return jsonify({'success': False, 'error': '没有上传文件或文件无效'}), 400
            
            # 创建信息库
            repository = repository_manager.create_repository(
                name=name,
                source=source,
                config_override={'description': description}
            )
            
            # 确保目录存在
            repository_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                         'data', 'crawled_data', name)
            os.makedirs(repository_dir, exist_ok=True)
            
            saved_files = []
            for i, file in enumerate(uploaded_files):
                if file.filename and file.filename.strip():
                    try:
                        # 增强的文件名处理，更好地支持跨平台
                        original_name = file.filename.strip()
                        
                        # 处理Windows路径分隔符
                        original_name = original_name.replace('\\', '/').split('/')[-1]
                        
                        name_part = os.path.splitext(original_name)[0]
                        ext_part = os.path.splitext(original_name)[1]
                        
                        # 检查文件类型
                        allowed_extensions = {'.txt', '.pdf', '.html', '.htm'}
                        file_ext = ext_part.lower()
                        
                        # 如果没有扩展名，尝试从MIME类型推断
                        if not file_ext:
                            content_type = getattr(file, 'content_type', getattr(file, 'mimetype', ''))
                            if 'text/plain' in content_type:
                                file_ext = '.txt'
                            elif 'application/pdf' in content_type:
                                file_ext = '.pdf'
                            elif 'text/html' in content_type:
                                file_ext = '.html'
                            else:
                                file_ext = '.txt'  # 默认
                        
                        if file_ext not in allowed_extensions:
                            logging.warning(f"跳过不支持的文件类型: {file.filename} (扩展名: {file_ext})")
                            continue
                        
                        # 增强的文件名清理函数，更好地处理Unicode和特殊字符
                        def enhanced_clean_filename(filename):
                            """增强的文件名清理，支持跨平台兼容性"""
                            import re
                            import unicodedata
                            
                            # 标准化Unicode字符
                            try:
                                filename = unicodedata.normalize('NFKD', filename)
                            except:
                                pass
                            
                            # 移除或替换危险字符，Windows和Unix系统都考虑
                            dangerous_chars = r'[<>:"/\\|?*\x00-\x1f]'
                            cleaned = re.sub(dangerous_chars, '_', filename)
                            
                            # 移除开头和结尾的空格和点
                            cleaned = cleaned.strip(' .')
                            
                            # 确保不为空
                            if not cleaned:
                                cleaned = f"file_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}"
                            
                            # Windows文件名长度限制
                            if len(cleaned) > 200:
                                cleaned = cleaned[:200]
                            
                            return cleaned
                        
                        # 使用增强的清理函数
                        safe_name_part = enhanced_clean_filename(name_part)
                        
                        # 最终文件名处理
                        if not safe_name_part or len(safe_name_part.strip()) < 1:
                            # 备选方案：使用secure_filename
                            try:
                                fallback_name = secure_filename(name_part)
                                if fallback_name and len(fallback_name) >= 1:
                                    safe_name_part = fallback_name
                                else:
                                    raise ValueError("Empty filename")
                            except:
                                # 最后的备选方案：使用时间戳
                                safe_name_part = f"uploaded_file_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}"
                        
                        # 重新组合文件名
                        filename = safe_name_part + file_ext.lower()
                        file_path = os.path.join(repository_dir, filename)
                        
                        # 处理文件名冲突
                        counter = 1
                        while os.path.exists(file_path):
                            filename = f"{safe_name_part}_{counter}{file_ext.lower()}"
                            file_path = os.path.join(repository_dir, filename)
                            counter += 1
                            if counter > 1000:  # 防止无限循环
                                filename = f"{safe_name_part}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}{file_ext.lower()}"
                                file_path = os.path.join(repository_dir, filename)
                                break
                        
                        # 保存文件，增加错误处理
                        try:
                            file.save(file_path)
                            file_size = os.path.getsize(file_path)
                            
                            # 验证文件确实保存成功
                            if file_size == 0:
                                os.remove(file_path)
                                logging.warning(f"文件 {original_name} 保存后大小为0，已删除")
                                continue
                            
                            saved_files.append({
                                'filename': filename,
                                'original_name': original_name,
                                'path': file_path,
                                'size': file_size
                            })
                            logging.info(f"成功保存文件: {original_name} -> {filename} (大小: {file_size} bytes)")
                            
                        except Exception as save_error:
                            logging.error(f"保存文件 {original_name} 失败: {str(save_error)}")
                            # 清理可能的部分文件
                            if os.path.exists(file_path):
                                try:
                                    os.remove(file_path)
                                except:
                                    pass
                            continue
                            
                    except Exception as process_error:
                        logging.error(f"处理文件 {file.filename} 失败: {str(process_error)}")
                        continue
            
            if not saved_files:
                return jsonify({'success': False, 'error': '没有有效的文件被保存，请检查文件格式和大小'}), 400
            
            # 更新信息库状态
            repository_manager.update_repository(name, {
                'status': 'complete',
                'uploaded_files': [f['filename'] for f in saved_files],
                'updated_at': datetime.now().isoformat()
            })
            
            return jsonify({
                'success': True,
                'repository': repository_manager.get_repository(name),
                'repository_name': name,
                'uploaded_files': [f['filename'] for f in saved_files],
                'message': f"成功上传 {len(saved_files)} 个文件"
            })
        
        else:
            # 处理JSON请求（爬虫方式）
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
        error_logs.add_error_log('repository', str(e), name if 'name' in locals() else None)
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
    """设置信息库直接入库模式"""
    try:
        data = request.json
        direct_import = data.get('direct_import')
        
        if direct_import is None:
            return jsonify({'success': False, 'error': '缺少 直接入库 参数'}), 400
        
        # 设置直接入库模式
        repository = repository_manager.set_direct_import(name, direct_import)
        
        return jsonify({
            'success': True,
            'repository': repository
        })
    
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logging.error(f"设置信息库直接入库模式失败: {str(e)}")
        error_logs.add_error_log('repository', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/repository/<name>/partial_sync', methods=['PUT'])
def set_repository_partial_sync(name):
    """设置信息库部分同步配置"""
    try:
        logging.info(f"接收到设置部分同步配置请求: repository={name}")
        
        data = request.get_json(silent=True)
        if not data:
            logging.error("请求数据为空或无效的JSON格式")
            return jsonify({'success': False, 'error': '请求数据为空或无效的JSON格式'}), 400
            
        logging.info(f"请求数据: {data}")
        
        partial_sync_enabled = data.get('partial_sync_enabled')
        failure_marker = data.get('failure_marker')
        
        logging.info(f"解析参数: partial_sync_enabled={partial_sync_enabled}, failure_marker={failure_marker}")
        
        if partial_sync_enabled is None:
            logging.error("缺少 partial_sync_enabled 参数")
            return jsonify({'success': False, 'error': '缺少 partial_sync_enabled 参数'}), 400
        
        # 设置部分同步配置
        logging.info(f"调用 repository_manager.set_partial_sync_config...")
        repository = repository_manager.set_partial_sync_config(name, partial_sync_enabled, failure_marker)
        logging.info(f"成功设置部分同步配置")
        
        return jsonify({
            'success': True,
            'repository': repository
        })
    
    except ValueError as e:
        logging.error(f"ValueError: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logging.error(f"设置信息库部分同步配置失败: {str(e)}")
        logging.error(f"异常类型: {type(e).__name__}")
        logging.error(f"异常详情: {str(e)}")
        import traceback
        logging.error(f"完整错误堆栈: {traceback.format_exc()}")
        error_logs.add_error_log('repository', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/repository/<name>/partial_sync', methods=['GET'])
def get_repository_partial_sync(name):
    """获取信息库部分同步配置"""
    try:
        # 获取部分同步配置
        config = repository_manager.get_partial_sync_config(name)
        
        return jsonify({
            'success': True,
            'config': config
        })
    
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logging.error(f"获取信息库部分同步配置失败: {str(e)}")
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

@api_blueprint.route('/repository/<name>/upload', methods=['POST'])
def upload_repository_files(name):
    """上传文件到信息库"""
    try:
        # 增强的调试日志
        logging.info(f"接收到文件上传请求: repository={name}")
        logging.info(f"request.content_type: {request.content_type}")
        logging.info(f"request.files keys: {list(request.files.keys())}")
        
        # 检查信息库是否存在
        repository = repository_manager.get_repository(name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {name}"}), 404
        
        # 增强的文件获取逻辑 - 尝试多种可能的字段名
        uploaded_files = []
        
        # 尝试多种可能的字段名，处理不同前端框架和浏览器的差异
        possible_field_names = ['files', 'files[]', 'file', 'upload', 'document']
        for field_name in possible_field_names:
            files = request.files.getlist(field_name)
            if files and any(f.filename for f in files):  # 确保文件有有效的文件名
                uploaded_files.extend(files)
                logging.info(f"从字段 '{field_name}' 获取到 {len(files)} 个文件")
        
        # 如果还是没有文件，遍历所有文件字段
        if not uploaded_files:
            for key in request.files.keys():
                files = request.files.getlist(key)
                valid_files = [f for f in files if f.filename and f.filename.strip()]
                if valid_files:
                    uploaded_files.extend(valid_files)
                    logging.info(f"从字段 '{key}' 获取到 {len(valid_files)} 个有效文件")
        
        logging.info(f"总共获取到的文件数量: {len(uploaded_files)}")
        for i, file in enumerate(uploaded_files):
            file_size = 0
            try:
                # 尝试获取文件大小
                file.seek(0, 2)  # 移动到文件末尾
                file_size = file.tell()
                file.seek(0)  # 重置到文件开头
            except:
                file_size = 0
            
            logging.info(f"文件 {i}: filename={file.filename}, content_type={getattr(file, 'content_type', getattr(file, 'mimetype', 'unknown'))}, size={file_size}")
        
        if not uploaded_files:
            return jsonify({'success': False, 'error': '没有上传文件或文件无效'}), 400
        
        # 获取信息库目录
        repository_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                     'data', 'crawled_data', name)
        
        # 确保目录存在
        os.makedirs(repository_dir, exist_ok=True)
        
        saved_files = []
        for i, file in enumerate(uploaded_files):
            if file.filename and file.filename.strip():
                try:
                    # 增强的文件名处理，更好地支持跨平台
                    original_name = file.filename.strip()
                    
                    # 处理Windows路径分隔符
                    original_name = original_name.replace('\\', '/').split('/')[-1]
                    
                    name_part = os.path.splitext(original_name)[0]
                    ext_part = os.path.splitext(original_name)[1]
                    
                    # 检查文件类型
                    allowed_extensions = {'.txt', '.pdf', '.html', '.htm'}
                    file_ext = ext_part.lower()
                    
                    # 如果没有扩展名，尝试从MIME类型推断
                    if not file_ext:
                        content_type = getattr(file, 'content_type', getattr(file, 'mimetype', ''))
                        if 'text/plain' in content_type:
                            file_ext = '.txt'
                        elif 'application/pdf' in content_type:
                            file_ext = '.pdf'
                        elif 'text/html' in content_type:
                            file_ext = '.html'
                        else:
                            file_ext = '.txt'  # 默认
                    
                    if file_ext not in allowed_extensions:
                        logging.warning(f"跳过不支持的文件类型: {file.filename} (扩展名: {file_ext})")
                        continue
                    
                    # 增强的文件名清理函数，更好地处理Unicode和特殊字符
                    def enhanced_clean_filename(filename):
                        """增强的文件名清理，支持跨平台兼容性"""
                        import re
                        import unicodedata
                        
                        # 标准化Unicode字符
                        try:
                            filename = unicodedata.normalize('NFKD', filename)
                        except:
                            pass
                        
                        # 移除或替换危险字符，Windows和Unix系统都考虑
                        dangerous_chars = r'[<>:"/\\|?*\x00-\x1f]'
                        cleaned = re.sub(dangerous_chars, '_', filename)
                        
                        # 移除开头和结尾的空格和点
                        cleaned = cleaned.strip(' .')
                        
                        # 确保不为空
                        if not cleaned:
                            cleaned = f"file_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}"
                        
                        # Windows文件名长度限制
                        if len(cleaned) > 200:
                            cleaned = cleaned[:200]
                        
                        return cleaned
                    
                    # 使用增强的清理函数
                    safe_name_part = enhanced_clean_filename(name_part)
                    
                    # 最终文件名处理
                    if not safe_name_part or len(safe_name_part.strip()) < 1:
                        # 备选方案：使用secure_filename
                        try:
                            fallback_name = secure_filename(name_part)
                            if fallback_name and len(fallback_name) >= 1:
                                safe_name_part = fallback_name
                            else:
                                raise ValueError("Empty filename")
                        except:
                            # 最后的备选方案：使用时间戳
                            safe_name_part = f"uploaded_file_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}"
                    
                    # 重新组合文件名
                    filename = safe_name_part + file_ext.lower()
                    file_path = os.path.join(repository_dir, filename)
                    
                    # 处理文件名冲突
                    counter = 1
                    while os.path.exists(file_path):
                        filename = f"{safe_name_part}_{counter}{file_ext.lower()}"
                        file_path = os.path.join(repository_dir, filename)
                        counter += 1
                        if counter > 1000:  # 防止无限循环
                            filename = f"{safe_name_part}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}{file_ext.lower()}"
                            file_path = os.path.join(repository_dir, filename)
                            break
                    
                    # 保存文件，增加错误处理
                    try:
                        file.save(file_path)
                        file_size = os.path.getsize(file_path)
                        
                        # 验证文件确实保存成功
                        if file_size == 0:
                            os.remove(file_path)
                            logging.warning(f"文件 {original_name} 保存后大小为0，已删除")
                            continue
                        
                        saved_files.append({
                            'filename': filename,
                            'original_name': original_name,
                            'path': file_path,
                            'size': file_size
                        })
                        logging.info(f"成功保存文件: {original_name} -> {filename} (大小: {file_size} bytes)")
                        
                    except Exception as save_error:
                        logging.error(f"保存文件 {original_name} 失败: {str(save_error)}")
                        # 清理可能的部分文件
                        if os.path.exists(file_path):
                            try:
                                os.remove(file_path)
                            except:
                                pass
                        continue
                            
                except Exception as process_error:
                    logging.error(f"处理文件 {file.filename} 失败: {str(process_error)}")
                    continue
        
        if not saved_files:
            return jsonify({'success': False, 'error': '没有有效的文件被保存，请检查文件格式和大小'}), 400
        
        # 更新信息库状态
        repository_manager.update_repository(name, {
            'updated_at': datetime.now().isoformat()
        })
        
        logging.info(f"成功上传 {len(saved_files)} 个文件到信息库 {name}")
        
        return jsonify({
            'success': True,
            'uploaded_files': saved_files,
            'message': f"成功上传 {len(saved_files)} 个文件"
        })
    
    except Exception as e:
        logging.error(f"上传文件失败: {str(e)}")
        error_logs.add_error_log('repository', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/repository/<name>/upload_url', methods=['POST'])
def upload_repository_url_file(name):
    """上传URL文件到信息库"""
    try:
        # 检查信息库是否存在
        repository = repository_manager.get_repository(name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {name}"}), 404
        
        data = request.json
        urls = data.get('urls', [])
        
        if not urls:
            return jsonify({'success': False, 'error': '没有提供URL'}), 400
        
        # 获取信息库目录
        repository_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                     'data', 'crawled_data', name)
        
        # 确保目录存在
        os.makedirs(repository_dir, exist_ok=True)
        
        # 创建URL文件
        url_filename = f"urls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        url_file_path = os.path.join(repository_dir, url_filename)
        
        with open(url_file_path, 'w', encoding='utf-8') as f:
            for url in urls:
                f.write(url.strip() + '\n')
        
        # 更新信息库状态
        repository_manager.update_repository(name, {
            'updated_at': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'url_file': url_filename,
            'urls_count': len(urls),
            'message': f"成功创建包含 {len(urls)} 个URL的文件"
        })
    
    except Exception as e:
        logging.error(f"上传URL文件失败: {str(e)}")
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

@api_blueprint.route('/repository/<name>/prompt_config', methods=['GET'])
def get_repository_prompt_config(name):
    """获取信息库Prompt配置"""
    try:
        # 检查信息库是否存在
        repository = repository_manager.get_repository(name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {name}"}), 404
        
        # 获取Prompt配置
        prompt_config = repository_manager.get_repository_prompt_config(name)
        
        return jsonify({
            'success': True,
            'prompt_config': prompt_config
        })
    
    except Exception as e:
        logging.error(f"获取信息库Prompt配置失败: {str(e)}")
        error_logs.add_error_log('repository', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/repository/<name>/prompt_config', methods=['PUT'])
def update_repository_prompt_config(name):
    """更新信息库Prompt配置"""
    try:
        data = request.json
        prompt_config = data.get('prompt_config', {})
        
        # 检查信息库是否存在
        repository = repository_manager.get_repository(name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {name}"}), 404
        
        # 更新Prompt配置
        updated_repository = repository_manager.update_repository_prompt_config(name, prompt_config)
        
        return jsonify({
            'success': True,
            'repository': updated_repository,
            'prompt_config': prompt_config
        })
    
    except Exception as e:
        logging.error(f"更新信息库Prompt配置失败: {str(e)}")
        error_logs.add_error_log('repository', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/repository/<name>/prompt_config/reset', methods=['POST'])
def reset_repository_prompt_config(name):
    """重置信息库Prompt配置为默认值"""
    try:
        # 检查信息库是否存在
        repository = repository_manager.get_repository(name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {name}"}), 404
        
        # 重置Prompt配置
        updated_repository = repository_manager.reset_repository_prompt_config(name)
        
        # 获取重置后的配置
        prompt_config = repository_manager.get_repository_prompt_config(name)
        
        return jsonify({
            'success': True,
            'repository': updated_repository,
            'prompt_config': prompt_config
        })
    
    except Exception as e:
        logging.error(f"重置信息库Prompt配置失败: {str(e)}")
        error_logs.add_error_log('repository', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_blueprint.route('/repository/<name>/prompt_config/sync_from_global', methods=['POST'])
def sync_repository_prompt_config_from_global(name):
    """从全局配置同步信息库Prompt配置"""
    try:
        # 检查信息库是否存在
        repository = repository_manager.get_repository(name)
        if not repository:
            return jsonify({'success': False, 'error': f"信息库不存在: {name}"}), 404
        
        # 获取全局配置
        from ..utils.config_loader import get_config
        global_config = get_config()
        global_prompt_config = global_config.get('processor', {})
        
        # 构建要同步的配置
        sync_config = {
            'summary_prompt': global_prompt_config.get('summary_prompt', ''),
            'summary_system_prompt': global_prompt_config.get('summary_system_prompt', ''),
            'qa_stages': global_prompt_config.get('qa_stages', {})
        }
        
        # 更新信息库配置
        updated_repository = repository_manager.update_repository_prompt_config(name, sync_config)
        
        return jsonify({
            'success': True,
            'repository': updated_repository,
            'prompt_config': sync_config
        })
    
    except Exception as e:
        logging.error(f"同步信息库Prompt配置失败: {str(e)}")
        error_logs.add_error_log('repository', str(e), name)
        return jsonify({'success': False, 'error': str(e)}), 500
