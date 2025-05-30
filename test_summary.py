#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import time

# API基础URL
BASE_URL = "http://localhost:5001/api"

# 测试生成总结
print("开始生成总结...")
response = requests.post(f"{BASE_URL}/processor/summary/generate", 
                        json={"repository_name": "test"})

if response.status_code == 200:
    result = response.json()
    if result.get('success'):
        task_id = result.get('task_id')
        print(f"任务已启动，任务ID: {task_id}")
        
        # 轮询任务状态
        while True:
            time.sleep(2)
            status_response = requests.get(f"{BASE_URL}/processor/status/{task_id}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                if status_data.get('success'):
                    status = status_data.get('status', {})
                    print(f"状态: {status.get('status')}, 进度: {status.get('processed_files')}/{status.get('total_files')}")
                    
                    if status.get('status') == 'completed':
                        print("总结生成完成！")
                        break
                    elif status.get('status') == 'failed':
                        print(f"总结生成失败: {status.get('error')}")
                        break
else:
    print(f"请求失败: {response.status_code}")
    print(response.text) 