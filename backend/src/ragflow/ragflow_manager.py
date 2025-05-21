#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RAGFlow 管理器模块

本模块负责与 RAGFlow API 交互，实现数据集管理、文档管理和解析管理等功能。
"""

import os
import json
import logging
import requests
import re
from datetime import datetime
from urllib.parse import urlparse

# 全局配置
config = {}
# API 客户端
client = None

def init(app_config):
    """
    初始化 RAGFlow 管理器
    
    Args:
        app_config: 应用配置
    """
    global config, client
    
    # 加载 RAGFlow 配置
    ragflow_config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                      'config', 'ragflow.yaml')
    
    if os.path.exists(ragflow_config_path):
        import yaml
        with open(ragflow_config_path, 'r', encoding='utf-8') as f:
            ragflow_config = yaml.safe_load(f)
        config.update(ragflow_config)
    
    # 合并应用配置
    if 'ragflow' in app_config:
        config.update(app_config['ragflow'])
    
    # 初始化 API 客户端
    client = RAGFlowClient(
        base_url=config.get('base_url', 'http://192.168.0.130'),
        api_key=os.environ.get('RAGFLOW_API_KEY') or config.get('api_key')
    )
    
    logging.info("RAGFlow 管理器初始化完成")

class RAGFlowAPIError(Exception):
    """RAGFlow API 错误"""
    def __init__(self, message, status_code=None, response_data=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data

class RAGFlowClient:
    """RAGFlow API 客户端"""
    
    def __init__(self, base_url=None, api_key=None):
        """
        初始化 RAGFlow 客户端
        
        Args:
            base_url: API 基础 URL
            api_key: API 密钥
        """
        self.base_url = base_url or os.getenv("RAGFLOW_BASE_URL", "http://192.168.0.130")
        self.api_key = api_key or os.getenv("RAGFLOW_API_KEY")
        
        if not self.api_key:
            logging.warning("未设置 RAGFLOW_API_KEY 环境变量或配置")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def request(self, method, endpoint, data=None, files=None, params=None, timeout=30):
        """
        发送 API 请求
        
        Args:
            method: 请求方法（GET, POST, PUT, DELETE）
            endpoint: API 端点
            data: 请求数据
            files: 上传文件
            params: 查询参数
            timeout: 超时时间（秒）
            
        Returns:
            dict: API 响应
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            headers = self.headers.copy()
            
            if files:
                # 上传文件时不设置 Content-Type，让 requests 自动设置
                headers.pop("Content-Type", None)
            
            response = requests.request(
                method,
                url,
                headers=headers,
                json=data if method.upper() != "GET" and not files else None,
                data=data if files else None,
                files=files,
                params=params,
                timeout=timeout
            )
            
            try:
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                # 提取详细错误信息
                error_message = f"RAGFlow API 请求失败: {e}"
                status_code = response.status_code
                response_data = None
                
                try:
                    response_data = response.json()
                    if response_data and "message" in response_data:
                        error_message = f"RAGFlow API 错误: {response_data['message']}"
                except:
                    pass
                
                raise RAGFlowAPIError(error_message, status_code, response_data)
        
        except requests.exceptions.RequestException as e:
            # 记录错误
            logging.error(f"RAGFlow API 请求失败: {e}")
            
            # 重试一次
            try:
                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    json=data if method.upper() != "GET" and not files else None,
                    data=data if files else None,
                    files=files,
                    params=params,
                    timeout=timeout
                )
                
                try:
                    response.raise_for_status()
                    return response.json()
                except requests.exceptions.HTTPError as e:
                    # 提取详细错误信息
                    error_message = f"RAGFlow API 请求失败: {e}"
                    status_code = response.status_code
                    response_data = None
                    
                    try:
                        response_data = response.json()
                        if response_data and "message" in response_data:
                            error_message = f"RAGFlow API 错误: {response_data['message']}"
                    except:
                        pass
                    
                    raise RAGFlowAPIError(error_message, status_code, response_data)
            
            except requests.exceptions.RequestException as e:
                logging.error(f"RAGFlow API 重试失败: {e}")
                raise RAGFlowAPIError(f"RAGFlow API 请求失败: {e}")

def list_datasets(page=1, page_size=30):
    """
    获取 Dataset 列表
    
    Args:
        page: 页码
        page_size: 每页数量
        
    Returns:
        dict: Dataset 列表
    """
    global client
    
    try:
        response = client.request(
            "GET",
            "/api/v1/datasets",
            params={"page": page, "page_size": page_size}
        )
        
        if response.get("code") == 0:
            return response.get("data", [])
        else:
            logging.error(f"获取 Dataset 列表失败: {response.get('message')}")
            return []
    
    except RAGFlowAPIError as e:
        logging.error(f"获取 Dataset 列表失败: {e}")
        return []
    except Exception as e:
        logging.error(f"获取 Dataset 列表异常: {str(e)}")
        return []

def create_dataset(name, embedding_model="jina-embeddings-v3", chunk_method="naive", parser_config=None):
    """
    创建 Dataset
    
    Args:
        name: Dataset 名称
        embedding_model: 嵌入模型
        chunk_method: 分块方法
        parser_config: 解析器配置
        
    Returns:
        dict: 创建结果
    """
    global client
    
    # 准备默认解析器配置
    default_parser_config = {
        "chunk_token_num": 128,
        "delimiter": "\\n!?;。；！？",
        "html4excel": False,
        "layout_recognize": True,
        "raptor": {
            "use_raptor": False
        }
    }
    
    # 合并解析器配置
    if parser_config:
        default_parser_config.update(parser_config)
    
    # 准备请求数据
    data = {
        "name": name,
        "avatar": "",
        "description": "",
        "embedding_model": embedding_model,
        "permission": "team",
        "chunk_method": chunk_method,
        "parser_config": default_parser_config
    }
    
    try:
        response = client.request("POST", "/api/v1/datasets", data=data)
        
        if response.get("code") == 0:
            logging.info(f"创建 Dataset 成功: {name}")
            return response.get("data", {})
        else:
            logging.error(f"创建 Dataset 失败: {response.get('message')}")
            raise RAGFlowAPIError(f"创建 Dataset 失败: {response.get('message')}")
    
    except RAGFlowAPIError as e:
        logging.error(f"创建 Dataset 失败: {e}")
        raise

def update_dataset(dataset_id, chunk_method=None, parser_config=None):
    """
    更新 Dataset
    
    Args:
        dataset_id: Dataset ID
        chunk_method: 分块方法
        parser_config: 解析器配置
        
    Returns:
        dict: 更新结果
    """
    global client
    
    data = {}
    
    if chunk_method:
        data["chunk_method"] = chunk_method
    
    if parser_config:
        data["parser_config"] = parser_config
    
    try:
        response = client.request("PUT", f"/api/v1/datasets/{dataset_id}", data=data)
        
        if response.get("code") == 0:
            logging.info(f"更新 Dataset 成功: {dataset_id}")
            return True
        else:
            logging.error(f"更新 Dataset 失败: {response.get('message')}")
            raise RAGFlowAPIError(f"更新 Dataset 失败: {response.get('message')}")
    
    except RAGFlowAPIError as e:
        logging.error(f"更新 Dataset 失败: {e}")
        raise

def delete_dataset(dataset_id):
    """
    删除 Dataset
    
    Args:
        dataset_id: Dataset ID
        
    Returns:
        bool: 是否成功
    """
    global client
    
    try:
        response = client.request("DELETE", f"/api/v1/datasets", data={"ids": [dataset_id]})
        
        if response.get("code") == 0:
            logging.info(f"删除 Dataset 成功: {dataset_id}")
            return True
        else:
            logging.error(f"删除 Dataset 失败: {response.get('message')}")
            raise RAGFlowAPIError(f"删除 Dataset 失败: {response.get('message')}")
    
    except RAGFlowAPIError as e:
        logging.error(f"删除 Dataset 失败: {e}")
        raise

def upload_document(dataset_id, file_path, chunk_method=None, parser_config=None):
    """
    上传文档
    
    Args:
        dataset_id: Dataset ID
        file_path: 文件路径
        chunk_method: 分块方法
        parser_config: 解析器配置
        
    Returns:
        dict: 上传结果
    """
    global client
    
    # 生成 metadata
    metadata = generate_metadata(os.path.basename(file_path))
    
    # 准备请求参数
    files = {'file': open(file_path, 'rb')}
    data = {}
    
    if chunk_method:
        data['chunk_method'] = chunk_method
    
    if parser_config:
        data['parser_config'] = json.dumps(parser_config)
    
    if metadata:
        data['meta_fields'] = json.dumps(metadata)
    
    try:
        response = client.request(
            "POST",
            f"/api/v1/datasets/{dataset_id}/documents",
            data=data,
            files=files
        )
        
        if response.get("code") == 0:
            logging.info(f"上传文档成功: {file_path} -> {dataset_id}")
            return response.get("data", [{}])[0]
        else:
            logging.error(f"上传文档失败: {response.get('message')}")
            raise RAGFlowAPIError(f"上传文档失败: {response.get('message')}")
    
    except RAGFlowAPIError as e:
        logging.error(f"上传文档失败: {e}")
        raise
    finally:
        # 确保文件关闭
        files['file'].close()

def update_document(dataset_id, document_id, chunk_method=None, parser_config=None):
    """
    更新文档
    
    Args:
        dataset_id: Dataset ID
        document_id: 文档 ID
        chunk_method: 分块方法
        parser_config: 解析器配置
        
    Returns:
        bool: 是否成功
    """
    global client
    
    data = {}
    
    if chunk_method:
        data["chunk_method"] = chunk_method
    
    if parser_config:
        data["parser_config"] = parser_config
    
    try:
        response = client.request(
            "PUT",
            f"/api/v1/datasets/{dataset_id}/documents/{document_id}",
            data=data
        )
        
        if response.get("code") == 0:
            logging.info(f"更新文档成功: {document_id}")
            return True
        else:
            logging.error(f"更新文档失败: {response.get('message')}")
            raise RAGFlowAPIError(f"更新文档失败: {response.get('message')}")
    
    except RAGFlowAPIError as e:
        logging.error(f"更新文档失败: {e}")
        raise

def delete_document(dataset_id, document_id):
    """
    删除文档
    
    Args:
        dataset_id: Dataset ID
        document_id: 文档 ID
        
    Returns:
        bool: 是否成功
    """
    global client
    
    try:
        response = client.request(
            "DELETE",
            f"/api/v1/datasets/{dataset_id}/documents",
            data={"ids": [document_id]}
        )
        
        if response.get("code") == 0:
            logging.info(f"删除文档成功: {document_id}")
            return True
        else:
            logging.error(f"删除文档失败: {response.get('message')}")
            raise RAGFlowAPIError(f"删除文档失败: {response.get('message')}")
    
    except RAGFlowAPIError as e:
        logging.error(f"删除文档失败: {e}")
        raise

def parse_documents(dataset_id):
    """
    解析文档
    
    Args:
        dataset_id: Dataset ID
        
    Returns:
        bool: 是否成功
    """
    global client
    
    try:
        response = client.request("POST", f"/api/v1/datasets/{dataset_id}/parse")
        
        if response.get("code") == 0:
            logging.info(f"解析文档成功: {dataset_id}")
            return True
        else:
            logging.error(f"解析文档失败: {response.get('message')}")
            raise RAGFlowAPIError(f"解析文档失败: {response.get('message')}")
    
    except RAGFlowAPIError as e:
        logging.error(f"解析文档失败: {e}")
        raise

def get_parse_status(dataset_id):
    """
    获取解析状态
    
    Args:
        dataset_id: Dataset ID
        
    Returns:
        dict: 解析状态
    """
    global client
    
    try:
        response = client.request("GET", f"/api/v1/datasets/{dataset_id}/parse/status")
        
        if response.get("code") == 0:
            return response.get("data", {})
        else:
            logging.error(f"获取解析状态失败: {response.get('message')}")
            return {}
    
    except RAGFlowAPIError as e:
        logging.error(f"获取解析状态失败: {e}")
        return {}

def generate_metadata(filename):
    """
    根据文件名生成 metadata
    
    Args:
        filename: 文件名（不含路径）
        
    Returns:
        dict: 包含 url 和 date_time 的字典，如果无法生成有效 URL 则返回 None
    """
    # 去除文件扩展名
    base_name = os.path.splitext(filename)[0]
    
    # 去除特定后缀
    if "_summarized_qa_csv" in base_name:
        base_name = base_name.replace("_summarized_qa_csv", "")
    elif "_summarized" in base_name:
        base_name = base_name.replace("_summarized", "")
    
    # 尝试转换为 URL
    potential_url = base_name.replace("_", ".")
    
    # 验证是否为合法 URL
    if is_valid_url(potential_url):
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:00:00")
        return {
            "url": potential_url,
            "date_time": current_time
        }
    
    # 如果不是合法 URL，返回 None
    return None

def is_valid_url(url):
    """
    检查字符串是否为合法 URL
    
    Args:
        url: 要检查的字符串
        
    Returns:
        bool: 是否为合法 URL
    """
    # URL 正则表达式模式
    pattern = re.compile(
        r'^(www\.)?'  # www. 是可选的
        r'(?!-)[A-Za-z0-9-]+'  # 域名部分不能以连字符开头
        r'(\.[A-Za-z0-9-]+)*'  # 子域名部分
        r'\.'  # 点号
        r'[A-Za-z]{2,}'  # 顶级域名至少2个字符
        r'(\/.*)?$'  # 路径部分是可选的
    )
    
    return bool(pattern.match(url))

def import_repository(repository_name, repository_config=None):
    """
    将信息库导入到 RAGFlow
    
    Args:
        repository_name: 信息库名称
        repository_config: 信息库配置
        
    Returns:
        dict: 导入结果
    """
    if repository_config is None:
        repository_config = {}
    
    # 检查信息库是否已有 Dataset ID
    if repository_config.get('dataset_id'):
        # 检查 Dataset 是否存在
        datasets = list_datasets()
        dataset_exists = False
        
        for dataset in datasets:
            if dataset.get('id') == repository_config['dataset_id']:
                dataset_exists = True
                break
        
        if dataset_exists:
            logging.info(f"信息库已有 Dataset: {repository_name} -> {repository_config['dataset_id']}")
            return {
                'success': True,
                'dataset_id': repository_config['dataset_id'],
                'action': 'existing'
            }
    
    # 创建 Dataset
    try:
        dataset = create_dataset(
            name=repository_name.replace('.', '_'),
            embedding_model=repository_config.get('embedding_model', 'jina-embeddings-v3'),
            chunk_method=repository_config.get('chunk_method', 'naive'),
            parser_config=repository_config.get('parser_config')
        )
        
        dataset_id = dataset.get('id')
        
        if not dataset_id:
            raise RAGFlowAPIError("创建 Dataset 失败，未返回 ID")
        
        # 获取信息库目录
        repository_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                     'data', 'crawled_data', repository_name)
        
        # 获取文件列表
        from ..repository import repository_manager
        files = repository_manager.get_repository_files(repository_name)
        
        if not files:
            logging.warning(f"信息库没有文件: {repository_name}")
            
            # 更新信息库配置
            repository_manager.update_repository(repository_name, {
                'dataset_id': dataset_id,
                'ragflow_synced': True,
                'updated_at': datetime.now().isoformat()
            })
            
            return {
                'success': True,
                'dataset_id': dataset_id,
                'action': 'created',
                'files_uploaded': 0
            }
        
        # 上传文件
        uploaded_files = 0
        
        for file in files:
            file_path = os.path.join(repository_dir, file['path'])
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                logging.warning(f"文件不存在: {file_path}")
                continue
            
            # 检查文件类型
            if not file['path'].endswith('.txt'):
                logging.info(f"跳过非文本文件: {file_path}")
                continue
            
            try:
                # 上传文件
                upload_document(dataset_id, file_path)
                uploaded_files += 1
            except Exception as e:
                logging.error(f"上传文件失败: {file_path}, 错误: {str(e)}")
        
        # 解析文档
        if uploaded_files > 0:
            try:
                parse_documents(dataset_id)
            except Exception as e:
                logging.error(f"解析文档失败: {str(e)}")
        
        # 更新信息库配置
        repository_manager.update_repository(repository_name, {
            'dataset_id': dataset_id,
            'ragflow_synced': True,
            'updated_at': datetime.now().isoformat()
        })
        
        return {
            'success': True,
            'dataset_id': dataset_id,
            'action': 'created',
            'files_uploaded': uploaded_files
        }
    
    except Exception as e:
        logging.error(f"导入信息库到 RAGFlow 失败: {str(e)}")
        raise

def sync_repository(repository_name, repository_config=None):
    """
    同步信息库到 RAGFlow
    
    Args:
        repository_name: 信息库名称
        repository_config: 信息库配置
        
    Returns:
        dict: 同步结果
    """
    if repository_config is None:
        # 获取信息库配置
        from ..repository import repository_manager
        repository = repository_manager.get_repository(repository_name)
        
        if not repository:
            raise ValueError(f"信息库不存在: {repository_name}")
        
        repository_config = repository
    
    # 检查是否已同步到 RAGFlow
    if not repository_config.get('dataset_id'):
        # 未同步，执行导入
        return import_repository(repository_name, repository_config)
    
    # 已同步，执行更新
    try:
        dataset_id = repository_config['dataset_id']
        
        # 检查 Dataset 是否存在
        datasets = list_datasets()
        dataset_exists = False
        
        for dataset in datasets:
            if dataset.get('id') == dataset_id:
                dataset_exists = True
                break
        
        if not dataset_exists:
            logging.warning(f"Dataset 不存在，重新创建: {dataset_id}")
            return import_repository(repository_name, {})
        
        # 获取信息库目录
        repository_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                     'data', 'crawled_data', repository_name)
        
        # 获取文件列表
        from ..repository import repository_manager
        files = repository_manager.get_repository_files(repository_name)
        
        if not files:
            logging.warning(f"信息库没有文件: {repository_name}")
            return {
                'success': True,
                'dataset_id': dataset_id,
                'action': 'updated',
                'files_uploaded': 0
            }
        
        # 上传文件
        uploaded_files = 0
        
        for file in files:
            file_path = os.path.join(repository_dir, file['path'])
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                logging.warning(f"文件不存在: {file_path}")
                continue
            
            # 检查文件类型
            if not file['path'].endswith('.txt'):
                logging.info(f"跳过非文本文件: {file_path}")
                continue
            
            try:
                # 上传文件
                upload_document(dataset_id, file_path)
                uploaded_files += 1
            except Exception as e:
                logging.error(f"上传文件失败: {file_path}, 错误: {str(e)}")
        
        # 解析文档
        if uploaded_files > 0:
            try:
                parse_documents(dataset_id)
            except Exception as e:
                logging.error(f"解析文档失败: {str(e)}")
        
        # 更新信息库配置
        repository_manager.update_repository(repository_name, {
            'ragflow_synced': True,
            'updated_at': datetime.now().isoformat()
        })
        
        return {
            'success': True,
            'dataset_id': dataset_id,
            'action': 'updated',
            'files_uploaded': uploaded_files
        }
    
    except Exception as e:
        logging.error(f"同步信息库到 RAGFlow 失败: {str(e)}")
        raise
