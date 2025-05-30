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
import hashlib
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
    
    # 初始化 API 客户端 - 优先使用api_base_url，然后是base_url
    base_url = config.get('api_base_url') or config.get('base_url', 'http://192.168.0.130')
    
    client = RAGFlowClient(
        base_url=base_url,
        api_key=os.environ.get('RAGFLOW_API_KEY') or config.get('api_key')
    )
    
    logging.info(f"RAGFlow 管理器初始化完成，使用URL: {base_url}")

def reload():
    """
    重新加载RAGFlow管理器配置
    
    从最新的配置文件重新初始化RAGFlow管理器
    """
    global config, client
    
    try:
        # 重新加载配置文件
        from ..utils.config_loader import get_config
        app_config = get_config()
        
        # 清空当前配置
        config.clear()
        
        # 重新初始化
        init(app_config)
        
        logging.info("RAGFlow 管理器配置重新加载完成")
        return True
        
    except Exception as e:
        logging.error(f"重新加载RAGFlow管理器配置失败: {str(e)}")
        return False

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
        chunk_method: 分块方法（上传后会单独设置）
        parser_config: 解析器配置（上传后会单独设置）
        
    Returns:
        dict: 上传结果
    """
    global client
    
    # 生成 metadata
    metadata = generate_metadata(os.path.basename(file_path))
    
    # 准备请求参数 - 根据RAGFlow API文档，上传时不设置chunk_method和parser_config
    files = {'file': open(file_path, 'rb')}
    data = {}
    
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
            document_data = response.get("data", [{}])[0]
            document_id = document_data.get("id")
            
            logging.info(f"上传文档成功: {file_path} -> {dataset_id}")
            
            # 如果指定了chunk_method或parser_config，上传后立即更新文档配置
            if (chunk_method or parser_config) and document_id:
                try:
                    update_document(dataset_id, document_id, chunk_method=chunk_method, parser_config=parser_config)
                    logging.info(f"更新文档配置成功: {document_id} -> chunk_method: {chunk_method}")
                except Exception as e:
                    logging.error(f"更新文档配置失败: {document_id}, 错误: {str(e)}")
            
            return document_data
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

def calculate_file_hash(file_path):
    """
    计算文件的MD5哈希值
    
    Args:
        file_path: 文件路径
        
    Returns:
        str: 文件的MD5哈希值
    """
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logging.error(f"计算文件哈希失败: {file_path}, 错误: {str(e)}")
        return None

def get_file_sync_status(repository_name, file_name):
    """
    获取文件的同步状态
    
    Args:
        repository_name: 信息库名称
        file_name: 文件名
        
    Returns:
        dict: 同步状态信息
    """
    from ..repository import repository_manager
    
    repository = repository_manager.get_repository(repository_name)
    if not repository:
        return None
    
    sync_status = repository.get('file_sync_status', {})
    return sync_status.get(file_name, None)

def update_file_sync_status(repository_name, file_name, file_hash, document_id, chunk_method):
    """
    更新文件的同步状态
    
    Args:
        repository_name: 信息库名称
        file_name: 文件名
        file_hash: 文件哈希值
        document_id: RAGFlow文档ID
        chunk_method: 使用的chunk方法
    """
    from ..repository import repository_manager
    
    repository = repository_manager.get_repository(repository_name)
    if not repository:
        return
    
    if 'file_sync_status' not in repository:
        repository['file_sync_status'] = {}
    
    repository['file_sync_status'][file_name] = {
        'file_hash': file_hash,
        'document_id': document_id,
        'chunk_method': chunk_method,
        'synced_at': datetime.now().isoformat(),
        'last_modified': datetime.now().isoformat()
    }
    
    # 保存更新
    repository_manager.update_repository(repository_name, {
        'file_sync_status': repository['file_sync_status']
    })

def check_file_needs_sync(repository_name, file_name, file_path, chunk_method, dataset_id):
    """
    检查文件是否需要同步
    
    Args:
        repository_name: 信息库名称
        file_name: 文件名
        file_path: 文件路径
        chunk_method: 要使用的chunk方法
        dataset_id: RAGFlow Dataset ID
        
    Returns:
        tuple: (需要同步, 原因, 现有文档ID)
    """
    global client
    
    # 计算当前文件哈希
    current_hash = calculate_file_hash(file_path)
    if not current_hash:
        return True, "无法计算文件哈希", None
    
    # 获取文件同步状态
    sync_status = get_file_sync_status(repository_name, file_name)
    
    if not sync_status:
        return True, "文件未曾同步", None
    
    # 检查文件是否发生变化
    if sync_status.get('file_hash') != current_hash:
        return True, "文件内容已变化", sync_status.get('document_id')
    
    # 检查chunk方法是否变化
    if sync_status.get('chunk_method') != chunk_method:
        return True, "chunk方法已变化", sync_status.get('document_id')
    
    # 检查RAGFlow中的文档是否还存在
    document_id = sync_status.get('document_id')
    if document_id:
        try:
            # 获取RAGFlow中的文档列表
            docs_response = client.request("GET", f"/api/v1/datasets/{dataset_id}/documents")
            if docs_response.get("code") == 0:
                existing_docs = docs_response.get("data", {}).get("docs", [])
                existing_doc_ids = {doc.get("id") for doc in existing_docs}
                
                if document_id not in existing_doc_ids:
                    return True, "文档在RAGFlow中已被删除", None
            else:
                logging.warning(f"无法获取RAGFlow文档列表: {docs_response.get('message')}")
                return True, "无法验证RAGFlow中的文档状态", document_id
        except Exception as e:
            logging.error(f"检查RAGFlow文档状态失败: {str(e)}")
            return True, "检查RAGFlow文档状态失败", document_id
    
    # 文件无需同步
    return False, "文件已是最新状态", document_id

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
    # 导入repository_manager
    from ..repository import repository_manager
    
    if repository_config is None:
        repository_config = {}
    
    # 获取直接入库设置
    direct_import = repository_config.get('direct_import', False)
    
    # 检查是否发生了模式切换
    last_sync_mode = repository_config.get('last_sync_mode')
    current_sync_mode = "direct_import" if direct_import else "processed_import"
    mode_switched = last_sync_mode and last_sync_mode != current_sync_mode
    
    if mode_switched:
        logging.warning(f"检测到同步模式切换: {last_sync_mode} -> {current_sync_mode}")
        # 清理RAGFlow中的所有文档，重新开始
        try:
            docs_response = client.request("GET", f"/api/v1/datasets/{repository_config['dataset_id']}/documents")
            if docs_response.get("code") == 0:
                existing_docs = docs_response.get("data", {}).get("docs", [])
                if existing_docs:
                    doc_ids = [doc.get("id") for doc in existing_docs if doc.get("id")]
                    if doc_ids:
                        # 批量删除所有现有文档
                        for doc_id in doc_ids:
                            try:
                                delete_document(repository_config['dataset_id'], doc_id)
                                logging.info(f"删除模式切换前的文档: {doc_id}")
                            except Exception as e:
                                logging.warning(f"删除文档失败: {doc_id}, 错误: {str(e)}")
                        
                        # 清理本地同步状态
                        repository_manager.update_repository(repository_name, {
                            'file_sync_status': {}
                        })
                        logging.info("已清理本地文件同步状态")
        except Exception as e:
            logging.error(f"清理模式切换文档失败: {str(e)}")
    
    # 获取文件类型映射
    file_type_mapping = repository_config.get('file_type_chunk_mapping', {})
    
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
            chunk_method='naive',  # 使用默认值，具体的 chunk method 在文件级别设置
            parser_config=None  # 不在 Dataset 级别设置 parser_config
        )
        
        dataset_id = dataset.get('id')
        
        if not dataset_id:
            raise RAGFlowAPIError("创建 Dataset 失败，未返回 ID")
        
        # 根据直接入库设置决定导入哪些文件
        if direct_import:
            # 直接入库：只导入源文件
            logging.info(f"直接入库模式：导入源文件到RAGFlow - {repository_name}")
            files = repository_manager.get_repository_files(repository_name)
            source_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                     'data', 'crawled_data', repository_name)
        else:
            # 非直接入库：只导入总结和问答对文件
            logging.info(f"处理后入库模式：导入总结和问答对文件到RAGFlow - {repository_name}")
            
            # 检查是否有总结文件
            summary_files = repository_manager.get_repository_summary_files(repository_name)
            qa_files = repository_manager.get_repository_qa_files(repository_name)
            
            if not summary_files and not qa_files:
                error_msg = "未找到总结文件或问答对文件，请先生成总结和问答对后再同步"
                logging.error(f"导入失败: {error_msg}")
                # 删除刚创建的空Dataset
                try:
                    delete_dataset(dataset_id)
                except:
                    pass
                raise RAGFlowAPIError(error_msg)
            
            # 合并总结和问答对文件
            files = []
            
            # 添加总结文件
            if summary_files:
                for summary_file in summary_files:
                    files.append({
                        'path': summary_file['path'],
                        'name': summary_file['name'],
                        'type': 'summary'
                    })
            
            # 添加问答对文件
            if qa_files:
                for qa_file in qa_files:
                    files.append({
                        'path': qa_file['path'],
                        'name': qa_file['name'],
                        'type': 'qa'
                    })
        
        if not files:
            if direct_import:
                logging.warning(f"信息库没有源文件: {repository_name}")
            else:
                logging.warning(f"信息库没有总结或问答对文件: {repository_name}")
            
            # 更新信息库配置
            repository_manager.update_repository(repository_name, {
                'dataset_id': dataset_id,
                'ragflow_synced': True,
                'updated_at': datetime.now().isoformat(),
                'last_sync_mode': current_sync_mode
            })
            
            return {
                'success': True,
                'dataset_id': dataset_id,
                'action': 'created',
                'files_uploaded': 0
            }
        
        # 上传文件
        uploaded_files = 0
        updated_files = 0
        skipped_files = 0
        
        # 系统文件过滤（仅在直接入库模式下使用）
        filtered_files = {
            'all_summaries.txt',
            'content_hashes.json'
        }
        
        filtered_prefixes = [
            'token_count_deepseek_',
            'token_count_gpt4o_',
            'token_count_jina_'
        ]
        
        for file in files:
            # 构建文件路径
            if direct_import:
                file_path = os.path.join(source_dir, file['path'])
                file_name = os.path.basename(file['path'])
            else:
                # 对于总结和问答对文件，直接使用完整路径
                file_path = file['path']
                file_name = file['name']
            
            file_ext = os.path.splitext(file_name)[1].lower()
            
            # 添加调试日志
            logging.info(f"处理文件: {file_name}, 扩展名: {file_ext}, 类型: {file.get('type', 'unknown')}")
            
            # 直接入库模式下需要过滤系统文件
            if direct_import:
                should_filter = False
                
                # 检查是否在过滤列表中
                if file_name in filtered_files:
                    should_filter = True
                
                # 检查是否以过滤前缀开头
                for prefix in filtered_prefixes:
                    if file_name.startswith(prefix):
                        should_filter = True
                        break
                
                # 如果需要过滤，跳过此文件
                if should_filter:
                    logging.info(f"跳过过滤文件: {file_name}")
                    continue
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                logging.warning(f"文件不存在: {file_path}")
                continue
            
            # 获取该文件类型的 chunk method 配置
            if direct_import:
                chunk_config = file_type_mapping.get(file_ext, {})
                chunk_method = chunk_config.get('chunk_method', 'naive')
                parser_config = chunk_config.get('parser_config', {})
            else:
                # 总结和问答对文件使用特定的配置
                if file.get('type') == 'qa' and file_ext == '.csv':
                    chunk_method = 'qa'
                    parser_config = {'raptor': {'use_raptor': False}}
                    logging.info(f"设置问答对CSV文件的chunk method为qa: {file_name}")
                elif file.get('type') == 'qa' and file_ext == '.json':
                    chunk_method = 'qa'
                    parser_config = {'raptor': {'use_raptor': False}}
                    logging.info(f"设置问答对JSON文件的chunk method为qa: {file_name}")
                else:
                    chunk_method = 'naive'
                    parser_config = {
                        'chunk_token_num': 256,
                        'delimiter': '\\n!?;。；！？',
                        'html4excel': False,
                        'layout_recognize': True,
                        'raptor': {'use_raptor': False}
                    }
                    logging.info(f"设置总结文件的chunk method为naive: {file_name}")
            
            logging.info(f"最终配置 - 文件: {file_name}, chunk_method: {chunk_method}")
            
            # 检查文件是否需要同步
            needs_sync, reason, existing_doc_id = check_file_needs_sync(
                repository_name, file_name, file_path, chunk_method, dataset_id
            )
            
            if not needs_sync:
                logging.info(f"跳过文件同步: {file_name} - {reason}")
                skipped_files += 1
                continue
            
            logging.info(f"需要同步文件: {file_name} - {reason}")
            
            try:
                document_id = None
                
                if existing_doc_id and reason in ["文件内容已变化", "chunk方法已变化"]:
                    # 文件已存在但需要更新，先删除旧文档
                    try:
                        delete_document(dataset_id, existing_doc_id)
                        logging.info(f"删除旧文档: {existing_doc_id}")
                    except Exception as e:
                        logging.warning(f"删除旧文档失败: {existing_doc_id}, 错误: {str(e)}")
                
                # 上传新文件
                document_data = upload_document(dataset_id, file_path, chunk_method=chunk_method, parser_config=parser_config)
                document_id = document_data.get("id")
                
                if document_id:
                    # 计算文件哈希并更新同步状态
                    file_hash = calculate_file_hash(file_path)
                    if file_hash:
                        update_file_sync_status(repository_name, file_name, file_hash, document_id, chunk_method)
                    
                    uploaded_files += 1
                    logging.info(f"上传文件成功: {file_name} -> chunk_method: {chunk_method}, document_id: {document_id}")
                else:
                    logging.error(f"上传文件失败，未获得文档ID: {file_name}")
                    
            except Exception as e:
                logging.error(f"处理文件失败: {file_path}, 错误: {str(e)}")
        
        # 触发文档解析
        if uploaded_files > 0:
            try:
                # 获取所有文档ID
                docs_response = client.request("GET", f"/api/v1/datasets/{dataset_id}/documents")
                if docs_response.get("code") == 0:
                    all_docs = docs_response.get("data", {}).get("docs", [])
                    doc_ids = [doc.get("id") for doc in all_docs if doc.get("id")]
                    
                    if doc_ids:
                        # 使用新的解析API
                        parse_response = client.request(
                            "POST", 
                            f"/api/v1/datasets/{dataset_id}/chunks",
                            data={"document_ids": doc_ids}
                        )
                        if parse_response.get("code") == 0:
                            logging.info(f"触发文档解析成功: {len(doc_ids)} 个文档")
                        else:
                            logging.error(f"触发文档解析失败: {parse_response.get('message')}")
            except Exception as e:
                logging.error(f"触发文档解析失败: {str(e)}")
        
        # 更新信息库配置
        repository_manager.update_repository(repository_name, {
            'ragflow_synced': True,
            'updated_at': datetime.now().isoformat(),
            'last_sync_mode': current_sync_mode
        })
        
        sync_mode = "直接入库" if direct_import else "处理后入库"
        return {
            'success': True,
            'dataset_id': dataset_id,
            'action': 'created',
            'files_uploaded': uploaded_files,
            'sync_mode': sync_mode
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
    # 导入repository_manager
    from ..repository import repository_manager
    
    # 清理过期的同步状态记录
    cleanup_sync_status(repository_name)
    
    if repository_config is None:
        # 获取信息库配置
        repository = repository_manager.get_repository(repository_name)
        
        if not repository:
            raise ValueError(f"信息库不存在: {repository_name}")
        
        repository_config = repository
    
    # 获取直接入库设置
    direct_import = repository_config.get('direct_import', False)
    
    # 检查是否发生了模式切换
    last_sync_mode = repository_config.get('last_sync_mode')
    current_sync_mode = "direct_import" if direct_import else "processed_import"
    mode_switched = last_sync_mode and last_sync_mode != current_sync_mode
    
    if mode_switched:
        logging.warning(f"检测到同步模式切换: {last_sync_mode} -> {current_sync_mode}")
        # 清理RAGFlow中的所有文档，重新开始
        try:
            docs_response = client.request("GET", f"/api/v1/datasets/{repository_config['dataset_id']}/documents")
            if docs_response.get("code") == 0:
                existing_docs = docs_response.get("data", {}).get("docs", [])
                if existing_docs:
                    doc_ids = [doc.get("id") for doc in existing_docs if doc.get("id")]
                    if doc_ids:
                        # 批量删除所有现有文档
                        for doc_id in doc_ids:
                            try:
                                delete_document(repository_config['dataset_id'], doc_id)
                                logging.info(f"删除模式切换前的文档: {doc_id}")
                            except Exception as e:
                                logging.warning(f"删除文档失败: {doc_id}, 错误: {str(e)}")
                        
                        # 清理本地同步状态
                        repository_manager.update_repository(repository_name, {
                            'file_sync_status': {}
                        })
                        logging.info("已清理本地文件同步状态")
        except Exception as e:
            logging.error(f"清理模式切换文档失败: {str(e)}")
    
    # 获取文件类型映射
    file_type_mapping = repository_config.get('file_type_chunk_mapping', {})
    
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
            return import_repository(repository_name, repository_config)
        
        # 根据直接入库设置决定同步哪些文件
        if direct_import:
            # 直接入库：只同步源文件
            logging.info(f"直接入库模式：同步源文件到RAGFlow - {repository_name}")
            files = repository_manager.get_repository_files(repository_name)
            source_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                     'data', 'crawled_data', repository_name)
        else:
            # 非直接入库：只同步总结和问答对文件
            logging.info(f"处理后入库模式：同步总结和问答对文件到RAGFlow - {repository_name}")
            
            # 检查是否有总结文件
            summary_files = repository_manager.get_repository_summary_files(repository_name)
            qa_files = repository_manager.get_repository_qa_files(repository_name)
            
            if not summary_files and not qa_files:
                error_msg = "未找到总结文件或问答对文件，请先生成总结和问答对后再同步"
                logging.error(f"同步失败: {error_msg}")
                raise RAGFlowAPIError(error_msg)
            
            # 合并总结和问答对文件
            files = []
            
            # 添加总结文件
            if summary_files:
                for summary_file in summary_files:
                    files.append({
                        'path': summary_file['path'],
                        'name': summary_file['name'],
                        'type': 'summary'
                    })
            
            # 添加问答对文件
            if qa_files:
                for qa_file in qa_files:
                    files.append({
                        'path': qa_file['path'],
                        'name': qa_file['name'],
                        'type': 'qa'
                    })
            
            # 设置基础目录
            if summary_files:
                source_dir = os.path.dirname(summary_files[0]['path'])
            elif qa_files:
                source_dir = os.path.dirname(qa_files[0]['path'])
            else:
                source_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                         'data', 'summarizer_output', repository_name)
        
        if not files:
            if direct_import:
                logging.warning(f"信息库没有源文件: {repository_name}")
            else:
                logging.warning(f"信息库没有总结或问答对文件: {repository_name}")
            return {
                'success': True,
                'dataset_id': dataset_id,
                'action': 'updated',
                'files_uploaded': 0
            }
        
        # 获取已上传的文档列表
        try:
            existing_docs_response = client.request("GET", f"/api/v1/datasets/{dataset_id}/documents")
            existing_docs = existing_docs_response.get("data", {}).get("docs", []) if existing_docs_response.get("code") == 0 else []
            existing_doc_names = {doc.get("name"): doc.get("id") for doc in existing_docs}
        except Exception as e:
            logging.error(f"获取已有文档列表失败: {str(e)}")
            existing_doc_names = {}
        
        # 上传文件
        uploaded_files = 0
        updated_files = 0
        skipped_files = 0
        
        # 系统文件过滤（仅在直接入库模式下使用）
        filtered_files = {
            'all_summaries.txt',
            'content_hashes.json'
        }
        
        filtered_prefixes = [
            'token_count_deepseek_',
            'token_count_gpt4o_',
            'token_count_jina_'
        ]
        
        for file in files:
            # 构建文件路径
            if direct_import:
                file_path = os.path.join(source_dir, file['path'])
                file_name = os.path.basename(file['path'])
            else:
                # 对于总结和问答对文件，直接使用完整路径
                file_path = file['path']
                file_name = file['name']
            
            file_ext = os.path.splitext(file_name)[1].lower()
            
            # 添加调试日志
            logging.info(f"处理文件: {file_name}, 扩展名: {file_ext}, 类型: {file.get('type', 'unknown')}")
            
            # 直接入库模式下需要过滤系统文件
            if direct_import:
                should_filter = False
                
                # 检查是否在过滤列表中
                if file_name in filtered_files:
                    should_filter = True
                
                # 检查是否以过滤前缀开头
                for prefix in filtered_prefixes:
                    if file_name.startswith(prefix):
                        should_filter = True
                        break
                
                # 如果需要过滤，跳过此文件
                if should_filter:
                    logging.info(f"跳过过滤文件: {file_name}")
                    continue
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                logging.warning(f"文件不存在: {file_path}")
                continue
            
            # 获取该文件类型的 chunk method 配置
            if direct_import:
                chunk_config = file_type_mapping.get(file_ext, {})
                chunk_method = chunk_config.get('chunk_method', 'naive')
                parser_config = chunk_config.get('parser_config', {})
            else:
                # 总结和问答对文件使用特定的配置
                if file.get('type') == 'qa' and file_ext == '.csv':
                    chunk_method = 'qa'
                    parser_config = {'raptor': {'use_raptor': False}}
                    logging.info(f"设置问答对CSV文件的chunk method为qa: {file_name}")
                elif file.get('type') == 'qa' and file_ext == '.json':
                    chunk_method = 'qa'
                    parser_config = {'raptor': {'use_raptor': False}}
                    logging.info(f"设置问答对JSON文件的chunk method为qa: {file_name}")
                else:
                    chunk_method = 'naive'
                    parser_config = {
                        'chunk_token_num': 256,
                        'delimiter': '\\n!?;。；！？',
                        'html4excel': False,
                        'layout_recognize': True,
                        'raptor': {'use_raptor': False}
                    }
                    logging.info(f"设置总结文件的chunk method为naive: {file_name}")
            
            logging.info(f"最终配置 - 文件: {file_name}, chunk_method: {chunk_method}")
            
            # 检查文件是否需要同步
            needs_sync, reason, existing_doc_id = check_file_needs_sync(
                repository_name, file_name, file_path, chunk_method, dataset_id
            )
            
            if not needs_sync:
                logging.info(f"跳过文件同步: {file_name} - {reason}")
                skipped_files += 1
                continue
            
            logging.info(f"需要同步文件: {file_name} - {reason}")
            
            try:
                document_id = None
                
                if existing_doc_id and reason in ["文件内容已变化", "chunk方法已变化"]:
                    # 文件已存在但需要更新，先删除旧文档
                    try:
                        delete_document(dataset_id, existing_doc_id)
                        logging.info(f"删除旧文档: {existing_doc_id}")
                    except Exception as e:
                        logging.warning(f"删除旧文档失败: {existing_doc_id}, 错误: {str(e)}")
                
                # 上传新文件
                document_data = upload_document(dataset_id, file_path, chunk_method=chunk_method, parser_config=parser_config)
                document_id = document_data.get("id")
                
                if document_id:
                    # 计算文件哈希并更新同步状态
                    file_hash = calculate_file_hash(file_path)
                    if file_hash:
                        update_file_sync_status(repository_name, file_name, file_hash, document_id, chunk_method)
                    
                    uploaded_files += 1
                    logging.info(f"上传文件成功: {file_name} -> chunk_method: {chunk_method}, document_id: {document_id}")
                else:
                    logging.error(f"上传文件失败，未获得文档ID: {file_name}")
                    
            except Exception as e:
                logging.error(f"处理文件失败: {file_path}, 错误: {str(e)}")
        
        # 触发文档解析
        if uploaded_files > 0:
            try:
                # 获取所有文档ID
                docs_response = client.request("GET", f"/api/v1/datasets/{dataset_id}/documents")
                if docs_response.get("code") == 0:
                    all_docs = docs_response.get("data", {}).get("docs", [])
                    doc_ids = [doc.get("id") for doc in all_docs if doc.get("id")]
                    
                    if doc_ids:
                        # 使用新的解析API
                        parse_response = client.request(
                            "POST", 
                            f"/api/v1/datasets/{dataset_id}/chunks",
                            data={"document_ids": doc_ids}
                        )
                        if parse_response.get("code") == 0:
                            logging.info(f"触发文档解析成功: {len(doc_ids)} 个文档")
                        else:
                            logging.error(f"触发文档解析失败: {parse_response.get('message')}")
            except Exception as e:
                logging.error(f"触发文档解析失败: {str(e)}")
        
        # 更新信息库配置
        repository_manager.update_repository(repository_name, {
            'ragflow_synced': True,
            'updated_at': datetime.now().isoformat(),
            'last_sync_mode': current_sync_mode
        })
        
        sync_mode = "直接入库" if direct_import else "处理后入库"
        return {
            'success': True,
            'dataset_id': dataset_id,
            'action': 'updated',
            'files_uploaded': uploaded_files,
            'files_updated': updated_files,
            'files_skipped': skipped_files,
            'sync_mode': sync_mode,
            'mode_switched': mode_switched,
            'mode_switch_info': f"从{last_sync_mode}切换到{current_sync_mode}" if mode_switched else None
        }
    
    except Exception as e:
        logging.error(f"同步信息库到 RAGFlow 失败: {str(e)}")
        raise

def cleanup_sync_status(repository_name):
    """
    清理信息库的文件同步状态，移除已不存在的文件记录
    
    Args:
        repository_name: 信息库名称
        
    Returns:
        int: 清理的记录数量
    """
    from ..repository import repository_manager
    
    repository = repository_manager.get_repository(repository_name)
    if not repository or 'file_sync_status' not in repository:
        return 0
    
    sync_status = repository['file_sync_status']
    cleaned_count = 0
    files_to_remove = []
    
    # 获取当前的文件列表
    try:
        # 根据直接入库设置获取相应的文件
        direct_import = repository.get('direct_import', False)
        
        if direct_import:
            current_files = repository_manager.get_repository_files(repository_name)
            current_file_names = {os.path.basename(f['path']) for f in current_files}
        else:
            summary_files = repository_manager.get_repository_summary_files(repository_name)
            qa_files = repository_manager.get_repository_qa_files(repository_name)
            current_file_names = set()
            
            for f in summary_files:
                current_file_names.add(f['name'])
            for f in qa_files:
                current_file_names.add(f['name'])
    except Exception as e:
        logging.error(f"获取当前文件列表失败: {str(e)}")
        return 0
    
    # 检查同步状态中的文件是否还存在
    for file_name in sync_status:
        if file_name not in current_file_names:
            files_to_remove.append(file_name)
            cleaned_count += 1
    
    # 移除不存在的文件记录
    for file_name in files_to_remove:
        del sync_status[file_name]
        logging.info(f"清理同步状态记录: {file_name}")
    
    # 如果有变化，保存更新
    if cleaned_count > 0:
        repository_manager.update_repository(repository_name, {
            'file_sync_status': sync_status
        })
        logging.info(f"清理了 {cleaned_count} 个过期的同步状态记录")
    
    return cleaned_count

def check_repository_sync_status(repository_name):
    """
    检查信息库与RAGFlow的同步状态
    
    Args:
        repository_name: 信息库名称
        
    Returns:
        dict: 同步状态检查结果
    """
    global client
    from ..repository import repository_manager
    
    result = {
        'repository_name': repository_name,
        'connection_status': 'unknown',
        'dataset_exists': False,
        'dataset_id': None,
        'file_count_match': False,
        'local_file_count': 0,
        'ragflow_file_count': 0,
        'direct_import': False,
        'sync_mode': 'unknown',
        'details': {},
        'errors': []
    }
    
    try:
        # 1. 检查信息库是否存在
        repository = repository_manager.get_repository(repository_name)
        if not repository:
            result['errors'].append(f"信息库不存在: {repository_name}")
            return result
        
        result['direct_import'] = repository.get('direct_import', False)
        result['sync_mode'] = "直接入库" if result['direct_import'] else "处理后入库"
        result['dataset_id'] = repository.get('dataset_id')
        
        # 2. 检查RAGFlow连接状况
        try:
            # 尝试获取Dataset列表来测试连接
            datasets = list_datasets(page=1, page_size=1)
            result['connection_status'] = 'connected'
            logging.info("RAGFlow连接正常")
        except Exception as e:
            result['connection_status'] = 'failed'
            result['errors'].append(f"RAGFlow连接失败: {str(e)}")
            logging.error(f"RAGFlow连接失败: {str(e)}")
            return result
        
        # 3. 检查Dataset是否存在
        if result['dataset_id']:
            try:
                # 获取所有Dataset并查找对应的Dataset
                all_datasets = list_datasets()
                dataset_found = None
                
                for dataset in all_datasets:
                    if dataset.get('id') == result['dataset_id']:
                        dataset_found = dataset
                        break
                
                if dataset_found:
                    result['dataset_exists'] = True
                    result['details']['dataset_name'] = dataset_found.get('name', '')
                    result['details']['dataset_chunk_count'] = dataset_found.get('chunk_count', 0)
                    result['details']['dataset_document_count'] = dataset_found.get('document_count', 0)
                    
                    # 获取RAGFlow中的文档数量
                    result['ragflow_file_count'] = dataset_found.get('document_count', 0)
                    
                    logging.info(f"找到对应的Dataset: {result['dataset_id']}, 文档数量: {result['ragflow_file_count']}")
                else:
                    result['dataset_exists'] = False
                    result['errors'].append(f"Dataset不存在: {result['dataset_id']}")
                    logging.warning(f"Dataset不存在: {result['dataset_id']}")
                    
            except Exception as e:
                result['errors'].append(f"检查Dataset状态失败: {str(e)}")
                logging.error(f"检查Dataset状态失败: {str(e)}")
        else:
            result['errors'].append("信息库未配置Dataset ID")
        
        # 4. 检查文件数量匹配情况
        if result['dataset_exists']:
            try:
                if result['direct_import']:
                    # 直接入库模式：检查源文件数量
                    source_files = repository_manager.get_repository_files(repository_name)
                    
                    # 过滤系统文件
                    filtered_files = {
                        'all_summaries.txt',
                        'content_hashes.json'
                    }
                    
                    filtered_prefixes = [
                        'token_count_deepseek_',
                        'token_count_gpt4o_',
                        'token_count_jina_'
                    ]
                    
                    valid_files = []
                    for file in source_files:
                        file_name = file['name']
                        should_filter = False
                        
                        # 检查是否在过滤列表中
                        if file_name in filtered_files:
                            should_filter = True
                        
                        # 检查是否以过滤前缀开头
                        for prefix in filtered_prefixes:
                            if file_name.startswith(prefix):
                                should_filter = True
                                break
                        
                        if not should_filter:
                            valid_files.append(file)
                    
                    result['local_file_count'] = len(valid_files)
                    result['details']['source_files'] = len(source_files)
                    result['details']['filtered_files'] = len(source_files) - len(valid_files)
                    
                    # 直接入库模式：RAGFlow文件数应该大于等于本地有效文件数
                    result['file_count_match'] = result['ragflow_file_count'] >= result['local_file_count']
                    
                    logging.info(f"直接入库模式 - 本地有效文件: {result['local_file_count']}, RAGFlow文件: {result['ragflow_file_count']}")
                    
                else:
                    # 处理后入库模式：检查总结文件和问答对文件数量
                    summary_files = repository_manager.get_repository_summary_files(repository_name)
                    qa_files = repository_manager.get_repository_qa_files(repository_name)
                    
                    # 只计算CSV格式的问答对文件
                    csv_qa_files = [f for f in qa_files if f.get('type') == 'csv' or f['name'].endswith('.csv')]
                    
                    result['local_file_count'] = len(summary_files) + len(csv_qa_files)
                    result['details']['summary_files'] = len(summary_files)
                    result['details']['qa_csv_files'] = len(csv_qa_files)
                    result['details']['qa_json_files'] = len(qa_files) - len(csv_qa_files)
                    
                    # 处理后入库模式：RAGFlow文件数应该等于总结文件数 + CSV问答对文件数
                    result['file_count_match'] = result['ragflow_file_count'] == result['local_file_count']
                    
                    logging.info(f"处理后入库模式 - 总结文件: {len(summary_files)}, CSV问答对: {len(csv_qa_files)}, 总计: {result['local_file_count']}, RAGFlow文件: {result['ragflow_file_count']}")
                
            except Exception as e:
                result['errors'].append(f"检查文件数量失败: {str(e)}")
                logging.error(f"检查文件数量失败: {str(e)}")
        
        # 5. 生成同步状态总结
        if result['connection_status'] == 'connected' and result['dataset_exists'] and result['file_count_match']:
            result['sync_status'] = 'synced'
            result['message'] = "信息库与RAGFlow完全同步"
        elif result['connection_status'] == 'failed':
            result['sync_status'] = 'connection_failed'
            result['message'] = "无法连接到RAGFlow"
        elif not result['dataset_exists']:
            result['sync_status'] = 'dataset_missing'
            result['message'] = "Dataset不存在或已被删除"
        elif not result['file_count_match']:
            result['sync_status'] = 'file_count_mismatch'
            if result['direct_import']:
                if result['ragflow_file_count'] < result['local_file_count']:
                    result['message'] = f"RAGFlow中文件数量不足（{result['ragflow_file_count']}/{result['local_file_count']}）"
                else:
                    result['message'] = f"RAGFlow中文件数量正常（{result['ragflow_file_count']}/{result['local_file_count']}）"
            else:
                result['message'] = f"RAGFlow中文件数量不匹配（{result['ragflow_file_count']}/{result['local_file_count']}）"
        else:
            result['sync_status'] = 'unknown'
            result['message'] = "同步状态未知"
        
        logging.info(f"信息库 {repository_name} 同步状态检查完成: {result['sync_status']}")
        
    except Exception as e:
        result['errors'].append(f"检查同步状态时发生异常: {str(e)}")
        result['sync_status'] = 'error'
        result['message'] = f"检查失败: {str(e)}"
        logging.error(f"检查信息库同步状态失败: {str(e)}")
    
    return result

def check_and_fix_mapping():
    """
    检查并修复信息库与RAGFlow Dataset的映射关系
    
    Returns:
        dict: 检查结果
    """
    from ..repository import repository_manager
    
    results = {
        'total_repositories': 0,
        'synced_repositories': 0,
        'orphaned_datasets': [],
        'missing_datasets': [],
        'fixed_mappings': []
    }
    
    try:
        # 获取所有信息库
        repositories = repository_manager.get_all_repositories()
        results['total_repositories'] = len(repositories)
        
        # 获取所有RAGFlow Datasets
        ragflow_datasets = list_datasets()
        ragflow_dataset_ids = {dataset.get('id'): dataset for dataset in ragflow_datasets}
        
        # 检查每个信息库的映射关系
        for repo in repositories:
            repo_name = repo.get('name')
            dataset_id = repo.get('dataset_id')
            
            if dataset_id:
                results['synced_repositories'] += 1
                
                # 检查Dataset是否还存在
                if dataset_id not in ragflow_dataset_ids:
                    results['missing_datasets'].append({
                        'repository': repo_name,
                        'dataset_id': dataset_id
                    })
                    
                    # 清除无效的dataset_id
                    try:
                        repository_manager.update_repository(repo_name, {
                            'dataset_id': None,
                            'ragflow_synced': False
                        })
                        results['fixed_mappings'].append({
                            'repository': repo_name,
                            'action': 'cleared_invalid_dataset_id'
                        })
                        logging.info(f"已清除信息库 {repo_name} 的无效Dataset ID: {dataset_id}")
                    except Exception as e:
                        logging.error(f"清除无效Dataset ID失败: {repo_name}, 错误: {str(e)}")
        
        # 检查孤儿Dataset（在RAGFlow中存在但没有对应的信息库）
        repository_names = {repo.get('name') for repo in repositories}
        synced_dataset_ids = {repo.get('dataset_id') for repo in repositories if repo.get('dataset_id')}
        
        for dataset_id, dataset in ragflow_dataset_ids.items():
            dataset_name = dataset.get('name', '')
            
            # 尝试从Dataset名称推断对应的信息库名称
            # RAGFlow中的Dataset名称通常是信息库名称的变体（替换了.为_）
            potential_repo_name = dataset_name.replace('_', '.')
            
            if (dataset_id not in synced_dataset_ids and 
                potential_repo_name not in repository_names):
                results['orphaned_datasets'].append({
                    'dataset_id': dataset_id,
                    'dataset_name': dataset_name,
                    'potential_repository': potential_repo_name
                })
        
        logging.info(f"映射关系检查完成: {results}")
        return results
        
    except Exception as e:
        logging.error(f"检查映射关系失败: {str(e)}")
        return {
            'error': str(e),
            'total_repositories': 0,
            'synced_repositories': 0,
            'orphaned_datasets': [],
            'missing_datasets': [],
            'fixed_mappings': []
        }

def cleanup_orphaned_datasets(dataset_ids):
    """
    清理孤儿Dataset
    
    Args:
        dataset_ids: 要删除的Dataset ID列表
        
    Returns:
        dict: 清理结果
    """
    results = {
        'success': True,
        'deleted_count': 0,
        'failed_deletions': []
    }
    
    for dataset_id in dataset_ids:
        try:
            delete_dataset(dataset_id)
            results['deleted_count'] += 1
            logging.info(f"已删除孤儿Dataset: {dataset_id}")
        except Exception as e:
            results['failed_deletions'].append({
                'dataset_id': dataset_id,
                'error': str(e)
            })
            logging.error(f"删除孤儿Dataset失败: {dataset_id}, 错误: {str(e)}")
    
    if results['failed_deletions']:
        results['success'] = False
    
    return results
