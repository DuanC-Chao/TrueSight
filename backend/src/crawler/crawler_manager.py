#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
爬虫管理器模块

本模块负责管理网页爬取任务，包括多线程并发爬取、树状深度爬取和增量爬取功能。
"""

import os
import time
import threading
import queue
import logging
import requests
import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import html2text
from datetime import datetime, timedelta

# 导入工具模块
from ..utils import url_utils, file_utils
from ..repository import repository_manager

# 全局配置
config = {}
# 爬取状态
crawl_status = {}
# 爬取队列
url_queue = queue.Queue()
# 已爬取URL集合
crawled_urls = set()
# 爬取锁
crawl_lock = threading.Lock()
# 屏蔽词列表
blocklist = []
# 最后文件入库时间记录
last_file_time = {}
# 文件入库监控线程
monitor_threads = {}

def init(app_config):
    """
    初始化爬虫管理器
    
    Args:
        app_config: 应用配置
    """
    global config, blocklist
    
    # 加载爬虫配置
    crawler_config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                      'config', 'crawler.yaml')
    
    if os.path.exists(crawler_config_path):
        import yaml
        with open(crawler_config_path, 'r', encoding='utf-8') as f:
            crawler_config = yaml.safe_load(f)
        config.update(crawler_config)
    
    # 合并应用配置
    if 'crawler' in app_config:
        config.update(app_config['crawler'])
        
        # 初始化屏蔽词列表
        if 'blocklist' in app_config['crawler'] and app_config['crawler']['blocklist']:
            blocklist = [line.strip() for line in app_config['crawler']['blocklist'].split('\n') if line.strip()]
            logging.info(f"已加载 {len(blocklist)} 个URL屏蔽词")
    
    logging.info("爬虫管理器初始化完成")

def start_crawl(urls, repository_name, max_depth=None, max_threads=None, incremental=False):
    """
    开始爬取任务
    
    Args:
        urls: URL列表或单个URL
        repository_name: 信息库名称
        max_depth: 最大爬取深度
        max_threads: 最大线程数
        incremental: 是否增量爬取
        
    Returns:
        task_id: 爬取任务ID
    """
    # 添加调试日志
    logging.info(f"start_crawl 被调用: repository_name={repository_name}, max_depth={max_depth}, max_threads={max_threads}, incremental={incremental}")
    
    # 生成任务ID
    task_id = f"crawl_{int(time.time())}"
    
    # 设置爬取参数
    if max_depth is None:
        max_depth = config.get('max_depth', 3)
        logging.info(f"max_depth 为 None，使用默认值: {max_depth}")
    else:
        logging.info(f"使用提供的 max_depth: {max_depth}")
    
    if max_threads is None:
        max_threads = config.get('max_threads', 10)
        logging.info(f"max_threads 为 None，使用默认值: {max_threads}")
    else:
        logging.info(f"使用提供的 max_threads: {max_threads}")
    
    # 初始化爬取状态
    crawl_status[task_id] = {
        'status': 'running',
        'repository_name': repository_name,
        'urls': urls if isinstance(urls, list) else [urls],
        'max_depth': max_depth,
        'max_threads': max_threads,
        'incremental': incremental,
        'start_time': datetime.now(),
        'end_time': None,
        'total_urls': 0,
        'crawled_urls': 0,
        'failed_urls': 0,
        'current_urls': [],
        'error': None
    }
    
    # 初始化最后文件入库时间
    global last_file_time
    last_file_time[task_id] = datetime.now()
    
    # 创建并启动爬取线程
    crawl_thread = threading.Thread(
        target=_crawl_worker,
        args=(task_id, urls, repository_name, max_depth, max_threads, incremental)
    )
    crawl_thread.daemon = True
    crawl_thread.start()
    
    # 创建并启动文件入库监控线程
    monitor_thread = threading.Thread(
        target=_monitor_file_inactivity,
        args=(task_id, repository_name)
    )
    monitor_thread.daemon = True
    monitor_thread.start()
    monitor_threads[task_id] = monitor_thread
    
    logging.info(f"爬取任务 {task_id} 已启动，信息库: {repository_name}, URLs: {urls}")
    
    return task_id

def _monitor_file_inactivity(task_id, repository_name):
    """
    监控文件入库活动，如果连续3分钟没有新文件入库，则将任务标记为完成
    
    Args:
        task_id: 爬取任务ID
        repository_name: 信息库名称
    """
    global last_file_time
    
    # 监控间隔（秒）
    check_interval = 30
    # 无活动超时时间（秒）
    inactivity_timeout = 180  # 3分钟
    
    while True:
        # 如果任务已经不是运行状态，退出监控
        if task_id not in crawl_status or crawl_status[task_id]['status'] != 'running':
            logging.info(f"任务 {task_id} 已不再运行，停止文件入库监控")
            break
        
        # 检查最后文件入库时间
        current_time = datetime.now()
        last_time = last_file_time.get(task_id)
        
        if last_time and (current_time - last_time).total_seconds() > inactivity_timeout:
            logging.info(f"任务 {task_id} 已连续 {inactivity_timeout} 秒没有新文件入库，自动标记为完成")
            
            # 更新任务状态
            crawl_status[task_id]['status'] = 'completed'
            crawl_status[task_id]['end_time'] = current_time
            
            # 更新信息库状态
            try:
                repository_manager.update_repository_status(repository_name, 'complete')
                logging.info(f"已将信息库 {repository_name} 状态更新为 complete")
            except Exception as e:
                logging.error(f"更新信息库状态失败: {str(e)}")
            
            # 退出监控
            break
        
        # 等待下一次检查
        time.sleep(check_interval)

def _crawl_worker(task_id, urls, repository_name, max_depth, max_threads, incremental):
    """
    爬取工作线程
    
    Args:
        task_id: 爬取任务ID
        urls: URL列表或单个URL
        repository_name: 信息库名称
        max_depth: 最大爬取深度
        max_threads: 最大线程数
        incremental: 是否增量爬取
    """
    try:
        # 准备URL列表
        if isinstance(urls, str):
            urls = [urls]
        
        # 创建信息库目录
        repository_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                     'data', 'crawled_data', repository_name)
        os.makedirs(repository_dir, exist_ok=True)
        
        # 初始化爬取队列和已爬取集合
        global url_queue, crawled_urls
        url_queue = queue.Queue()
        crawled_urls = set()
        
        # 如果是增量爬取，加载已爬取的URL
        if incremental:
            existing_files = file_utils.list_files(repository_dir, ['.txt', '.pdf', '.html'])
            for file_path in existing_files:
                file_name = os.path.basename(file_path)
                url = url_utils.filename_to_url(file_name)
                if url:
                    crawled_urls.add(url)
        
        # 将起始URL加入队列
        for url in urls:
            url_queue.put((url, 0))  # (url, depth)
        
        # 更新任务状态
        crawl_status[task_id]['total_urls'] = url_queue.qsize()
        
        # 创建工作线程池
        threads = []
        for i in range(max_threads):
            t = threading.Thread(
                target=_crawl_thread,
                args=(task_id, repository_dir, max_depth)
            )
            t.daemon = True
            t.start()
            threads.append(t)
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 更新任务状态
        crawl_status[task_id]['status'] = 'completed'
        crawl_status[task_id]['end_time'] = datetime.now()
        
        # 更新信息库状态
        try:
            repository_manager.update_repository_status(repository_name, 'complete')
            logging.info(f"已将信息库 {repository_name} 状态更新为 complete")
        except Exception as e:
            logging.error(f"更新信息库状态失败: {str(e)}")
        
        logging.info(f"爬取任务 {task_id} 已完成，信息库: {repository_name}")
    
    except Exception as e:
        # 更新任务状态为失败
        crawl_status[task_id]['status'] = 'failed'
        crawl_status[task_id]['error'] = str(e)
        crawl_status[task_id]['end_time'] = datetime.now()
        
        logging.error(f"爬取任务 {task_id} 失败: {str(e)}")

def _crawl_thread(task_id, repository_dir, max_depth):
    """
    爬取线程
    
    Args:
        task_id: 爬取任务ID
        repository_dir: 信息库目录
        max_depth: 最大爬取深度
    """
    while True:
        try:
            # 从队列获取URL
            url, depth = url_queue.get(block=False)
            
            # 更新当前爬取的URL
            with crawl_lock:
                if url not in crawl_status[task_id]['current_urls']:
                    crawl_status[task_id]['current_urls'].append(url)
            
            # 检查URL是否已爬取
            if url in crawled_urls:
                url_queue.task_done()
                continue
            
            # 爬取URL
            try:
                # 检查是否是PDF文件
                is_pdf = url.lower().endswith('.pdf')
                
                if is_pdf:
                    # 直接下载PDF文件，不受屏蔽词限制
                    _download_pdf(url, repository_dir, task_id)
                    
                    # 标记URL为已爬取
                    with crawl_lock:
                        crawled_urls.add(url)
                        crawl_status[task_id]['crawled_urls'] += 1
                        if url in crawl_status[task_id]['current_urls']:
                            crawl_status[task_id]['current_urls'].remove(url)
                else:
                    # 爬取普通网页
                    content, links = _crawl_url(url)
                    
                    # 检查URL是否包含屏蔽词
                    should_save = not _is_url_blocked(url)
                    
                    # 保存内容（如果不在屏蔽列表中）
                    if content and should_save:
                        file_path = _save_content(url, content, repository_dir, task_id)
                    
                    # 标记URL为已爬取
                    with crawl_lock:
                        crawled_urls.add(url)
                        if should_save:
                            crawl_status[task_id]['crawled_urls'] += 1
                        if url in crawl_status[task_id]['current_urls']:
                            crawl_status[task_id]['current_urls'].remove(url)
                    
                    # 如果深度未达到最大值，将链接加入队列
                    if depth < max_depth:
                        for link in links:
                            if link not in crawled_urls:
                                url_queue.put((link, depth + 1))
                                with crawl_lock:
                                    crawl_status[task_id]['total_urls'] += 1
                
            except Exception as e:
                logging.error(f"爬取URL失败: {url}, 错误: {str(e)}")
                with crawl_lock:
                    crawl_status[task_id]['failed_urls'] += 1
                    if url in crawl_status[task_id]['current_urls']:
                        crawl_status[task_id]['current_urls'].remove(url)
            
            # 标记任务完成
            url_queue.task_done()
        
        except queue.Empty:
            # 队列为空，退出线程
            break

def _download_pdf(url, repository_dir, task_id=None):
    """
    下载PDF文件
    
    Args:
        url: PDF文件URL
        repository_dir: 信息库目录
        task_id: 爬取任务ID
        
    Returns:
        file_path: 保存的文件路径
    """
    # 设置请求头
    headers = {
        'User-Agent': config.get('user_agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36')
    }
    
    # 发送请求
    response = requests.get(
        url, 
        headers=headers, 
        timeout=config.get('timeout', 30),
        verify=False,  # 忽略SSL证书验证
        stream=True    # 流式下载
    )
    
    # 检查响应状态
    response.raise_for_status()
    
    # 将URL转换为文件名
    file_name = url_utils.url_to_filename(url)
    
    # 保存为PDF文件
    file_path = os.path.join(repository_dir, f"{file_name}.pdf")
    with open(file_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    
    # 更新最后文件入库时间
    if task_id:
        global last_file_time
        last_file_time[task_id] = datetime.now()
    
    logging.info(f"已下载PDF文件: {url} -> {file_path}")
    
    return file_path

def _is_url_blocked(url):
    """
    检查URL是否包含屏蔽词
    
    Args:
        url: 要检查的URL
        
    Returns:
        bool: 是否被屏蔽
    """
    if not blocklist:
        return False
    
    for pattern in blocklist:
        try:
            if re.search(pattern, url):
                logging.info(f"URL被屏蔽词'{pattern}'屏蔽: {url}")
                return True
        except re.error:
            # 如果正则表达式无效，则作为普通字符串匹配
            if pattern in url:
                logging.info(f"URL被屏蔽词'{pattern}'屏蔽: {url}")
                return True
    
    return False

def _crawl_url(url):
    """
    爬取单个URL
    
    Args:
        url: 要爬取的URL
        
    Returns:
        content: 页面内容
        links: 页面中的链接
    """
    # 设置请求头
    headers = {
        'User-Agent': config.get('user_agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36')
    }
    
    # 发送请求
    response = requests.get(
        url, 
        headers=headers, 
        timeout=config.get('timeout', 30),
        verify=False  # 忽略SSL证书验证
    )
    
    # 检查响应状态
    response.raise_for_status()
    
    # 解析页面内容
    soup = BeautifulSoup(response.text, 'lxml')
    
    # 提取正文内容
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.ignore_tables = False
    content = h.handle(response.text)
    
    # 提取链接
    links = []
    for a_tag in soup.find_all('a', href=True):
        link = a_tag['href']
        # 处理相对URL
        if not link.startswith(('http://', 'https://')):
            link = urljoin(url, link)
        
        # 过滤链接
        if _should_crawl_url(link, url):
            links.append(link)
    
    return content, links

def _should_crawl_url(url, parent_url):
    """
    判断URL是否应该爬取
    
    Args:
        url: 要判断的URL
        parent_url: 父URL
        
    Returns:
        bool: 是否应该爬取
    """
    # 解析URL
    parsed_url = urlparse(url)
    parsed_parent = urlparse(parent_url)
    
    # 检查是否是同一域名
    if parsed_url.netloc != parsed_parent.netloc:
        return False
    
    # 检查URL格式
    if not parsed_url.scheme in ('http', 'https'):
        return False
    
    # 检查文件类型
    path = parsed_url.path.lower()
    excluded_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.xml', '.json']
    if any(path.endswith(ext) for ext in excluded_extensions):
        return False
    
    return True

def _save_content(url, content, repository_dir, task_id=None):
    """
    保存爬取内容
    
    Args:
        url: 爬取的URL
        content: 页面内容
        repository_dir: 信息库目录
        task_id: 爬取任务ID
        
    Returns:
        file_path: 保存的文件路径
    """
    # 将URL转换为文件名
    file_name = url_utils.url_to_filename(url)
    
    # 保存为文本文件
    file_path = os.path.join(repository_dir, f"{file_name}.txt")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 更新最后文件入库时间
    if task_id:
        global last_file_time
        last_file_time[task_id] = datetime.now()
    
    return file_path

def get_crawl_status(task_id):
    """
    获取爬取任务状态
    
    Args:
        task_id: 爬取任务ID
        
    Returns:
        status: 任务状态
    """
    if task_id in crawl_status:
        return crawl_status[task_id]
    else:
        return None

def pause_crawl(task_id):
    """
    暂停爬取任务
    
    Args:
        task_id: 爬取任务ID
        
    Returns:
        success: 是否成功
    """
    if task_id in crawl_status and crawl_status[task_id]['status'] == 'running':
        crawl_status[task_id]['status'] = 'paused'
        return True
    return False

def resume_crawl(task_id):
    """
    恢复爬取任务
    
    Args:
        task_id: 爬取任务ID
        
    Returns:
        success: 是否成功
    """
    if task_id in crawl_status and crawl_status[task_id]['status'] == 'paused':
        crawl_status[task_id]['status'] = 'running'
        return True
    return False

def stop_crawl(task_id):
    """
    停止爬取任务
    
    Args:
        task_id: 爬取任务ID
        
    Returns:
        success: 是否成功
    """
    if task_id in crawl_status and crawl_status[task_id]['status'] in ['running', 'paused']:
        crawl_status[task_id]['status'] = 'stopped'
        crawl_status[task_id]['end_time'] = datetime.now()
        return True
    return False
