#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TrueSight 主程序入口

本模块是TrueSight后端服务的主入口，负责初始化应用、配置服务和启动Web服务器。
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging
import yaml
from flask import Flask, jsonify
from flask_cors import CORS
from gevent.pywsgi import WSGIServer

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入TrueSight模块
from .crawler import crawler_manager
from .processor import processor_manager
from .repository import repository_manager
from .ragflow import ragflow_manager
from .scheduler import scheduler_manager
from .api import api_blueprint
from .utils import config_loader, logger_setup

# 创建Flask应用
app = Flask(__name__)
CORS(app)  # 启用跨域支持

# 注册API蓝图
app.register_blueprint(api_blueprint, url_prefix='/api')

# 健康检查路由
@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'ok',
        'version': '1.0.0',
        'service': 'TrueSight'
    })

def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'config.yaml')
    
    if not os.path.exists(config_path):
        logging.error(f"配置文件不存在: {config_path}")
        sys.exit(1)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config

def init_app():
    """初始化应用"""
    # 加载配置
    config = load_config()
    
    # 设置日志
    logger_setup.setup_logger(config.get('log_level', 'INFO'))
    
    # 初始化各个管理器
    crawler_manager.init(config)
    processor_manager.init(config)
    repository_manager.init(config)
    ragflow_manager.init(config)
    scheduler_manager.init(config)
    
    return config

def main():
    """主函数"""
    # 初始化应用
    config = init_app()
    
    # 获取服务器配置
    host = config.get('server', {}).get('host', '0.0.0.0')
    port = config.get('server', {}).get('port', 5001)
    debug = config.get('debug', False)
    
    if debug:
        # 开发模式：使用Flask内置服务器
        app.run(host=host, port=port, debug=True)
    else:
        # 生产模式：使用Gevent WSGI服务器
        logging.info(f"TrueSight服务启动于 http://{host}:{port}")
        http_server = WSGIServer((host, port), app)
        http_server.serve_forever()

if __name__ == '__main__':
    main()
