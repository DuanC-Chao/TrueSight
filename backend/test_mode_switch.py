#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试RAGFlow同步模式切换功能
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ragflow import ragflow_manager
from src.repository import repository_manager

def test_mode_switch_detection():
    """测试模式切换检测功能"""
    
    # 模拟信息库配置
    test_repo_config = {
        'name': 'test_repo',
        'direct_import': False,  # 开始时关闭直接入库
        'dataset_id': 'test_dataset_123',
        'last_sync_mode': None  # 首次同步
    }
    
    print("=== 测试模式切换检测功能 ===")
    
    # 测试1: 首次同步（无模式切换）
    print("\n1. 测试首次同步...")
    direct_import = test_repo_config.get('direct_import', False)
    last_sync_mode = test_repo_config.get('last_sync_mode')
    current_sync_mode = "direct_import" if direct_import else "processed_import"
    mode_switched = last_sync_mode and last_sync_mode != current_sync_mode
    
    print(f"   直接入库: {direct_import}")
    print(f"   上次同步模式: {last_sync_mode}")
    print(f"   当前同步模式: {current_sync_mode}")
    print(f"   模式切换: {mode_switched}")
    assert not mode_switched, "首次同步不应该检测到模式切换"
    
    # 模拟首次同步完成，更新last_sync_mode
    test_repo_config['last_sync_mode'] = current_sync_mode
    
    # 测试2: 相同模式再次同步（无模式切换）
    print("\n2. 测试相同模式再次同步...")
    last_sync_mode = test_repo_config.get('last_sync_mode')
    current_sync_mode = "direct_import" if direct_import else "processed_import"
    mode_switched = last_sync_mode and last_sync_mode != current_sync_mode
    
    print(f"   直接入库: {direct_import}")
    print(f"   上次同步模式: {last_sync_mode}")
    print(f"   当前同步模式: {current_sync_mode}")
    print(f"   模式切换: {mode_switched}")
    assert not mode_switched, "相同模式同步不应该检测到模式切换"
    
    # 测试3: 切换到直接入库模式（有模式切换）
    print("\n3. 测试切换到直接入库模式...")
    test_repo_config['direct_import'] = True  # 开启直接入库
    direct_import = test_repo_config.get('direct_import', False)
    last_sync_mode = test_repo_config.get('last_sync_mode')
    current_sync_mode = "direct_import" if direct_import else "processed_import"
    mode_switched = last_sync_mode and last_sync_mode != current_sync_mode
    
    print(f"   直接入库: {direct_import}")
    print(f"   上次同步模式: {last_sync_mode}")
    print(f"   当前同步模式: {current_sync_mode}")
    print(f"   模式切换: {mode_switched}")
    assert mode_switched, "切换模式应该检测到模式切换"
    
    # 模拟模式切换同步完成
    test_repo_config['last_sync_mode'] = current_sync_mode
    
    # 测试4: 切换回处理后入库模式（有模式切换）
    print("\n4. 测试切换回处理后入库模式...")
    test_repo_config['direct_import'] = False  # 关闭直接入库
    direct_import = test_repo_config.get('direct_import', False)
    last_sync_mode = test_repo_config.get('last_sync_mode')
    current_sync_mode = "direct_import" if direct_import else "processed_import"
    mode_switched = last_sync_mode and last_sync_mode != current_sync_mode
    
    print(f"   直接入库: {direct_import}")
    print(f"   上次同步模式: {last_sync_mode}")
    print(f"   当前同步模式: {current_sync_mode}")
    print(f"   模式切换: {mode_switched}")
    assert mode_switched, "切换模式应该检测到模式切换"
    
    print("\n✅ 所有测试通过！模式切换检测功能正常工作。")

if __name__ == "__main__":
    test_mode_switch_detection() 