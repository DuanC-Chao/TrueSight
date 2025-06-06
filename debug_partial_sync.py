#!/usr/bin/env python3
"""
部分同步配置调试脚本
用于测试和诊断部分同步配置保存问题
"""

import sys
import os

# 添加后端路径到sys.path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

def test_repository_manager():
    """测试repository_manager的部分同步配置功能"""
    print("🔍 测试 repository_manager 部分同步配置功能...")
    
    try:
        # 导入模块
        from src.repository import repository_manager
        
        print("✅ 成功导入 repository_manager")
        
        # 初始化（使用空配置）
        repository_manager.init({})
        print("✅ 成功初始化 repository_manager")
        
        # 获取所有信息库
        repositories = repository_manager.get_all_repositories()
        print(f"📚 找到 {len(repositories)} 个信息库:")
        for repo in repositories:
            print(f"   - {repo['name']} (来源: {repo.get('source', '未知')})")
        
        if not repositories:
            print("❌ 没有找到信息库，请先创建一个信息库")
            return False
        
        # 选择第一个信息库进行测试
        test_repo = repositories[0]
        repo_name = test_repo['name']
        print(f"\n🧪 使用信息库 '{repo_name}' 进行测试")
        
        # 测试获取当前配置
        try:
            current_config = repository_manager.get_partial_sync_config(repo_name)
            print(f"✅ 当前部分同步配置: {current_config}")
        except Exception as e:
            print(f"❌ 获取当前配置失败: {str(e)}")
            return False
        
        # 测试设置配置 - 启用
        try:
            print("\n🔧 测试设置部分同步配置 (启用)...")
            updated_repo = repository_manager.set_partial_sync_config(
                repo_name, 
                True, 
                "测试失败标识文本"
            )
            print("✅ 成功设置部分同步配置 (启用)")
            print(f"   partial_sync_enabled: {updated_repo.get('partial_sync_enabled')}")
            print(f"   failure_marker: {updated_repo.get('failure_marker')}")
        except Exception as e:
            print(f"❌ 设置配置失败: {str(e)}")
            import traceback
            print(f"完整错误: {traceback.format_exc()}")
            return False
        
        # 测试设置配置 - 禁用
        try:
            print("\n🔧 测试设置部分同步配置 (禁用)...")
            updated_repo = repository_manager.set_partial_sync_config(
                repo_name, 
                False, 
                None
            )
            print("✅ 成功设置部分同步配置 (禁用)")
            print(f"   partial_sync_enabled: {updated_repo.get('partial_sync_enabled')}")
        except Exception as e:
            print(f"❌ 设置配置失败: {str(e)}")
            import traceback
            print(f"完整错误: {traceback.format_exc()}")
            return False
        
        print("\n🎉 所有测试通过！repository_manager 工作正常")
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {str(e)}")
        print("请确保在 TrueSight 项目根目录运行此脚本")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        print(f"完整错误: {traceback.format_exc()}")
        return False

def test_data_directory():
    """测试数据目录权限"""
    print("\n🔍 测试数据目录权限...")
    
    data_dir = os.path.join(os.path.dirname(__file__), 'data', 'crawled_data')
    
    if not os.path.exists(data_dir):
        print(f"📁 数据目录不存在: {data_dir}")
        try:
            os.makedirs(data_dir, exist_ok=True)
            print(f"✅ 成功创建数据目录: {data_dir}")
        except Exception as e:
            print(f"❌ 创建数据目录失败: {str(e)}")
            return False
    else:
        print(f"📁 数据目录存在: {data_dir}")
    
    # 测试写入权限
    test_file = os.path.join(data_dir, '.write_test')
    try:
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        print("✅ 数据目录写入权限正常")
        return True
    except Exception as e:
        print(f"❌ 数据目录写入权限测试失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("🚀 TrueSight 部分同步配置调试脚本")
    print("=" * 50)
    
    # 测试数据目录
    if not test_data_directory():
        print("\n❌ 数据目录测试失败，程序退出")
        sys.exit(1)
    
    # 测试repository_manager
    if not test_repository_manager():
        print("\n❌ repository_manager 测试失败，程序退出")
        sys.exit(1)
    
    print("\n🎉 所有测试通过！")
    print("\n📋 如果前端仍然报错，请：")
    print("1. 打开浏览器开发者工具的Console标签页")
    print("2. 尝试保存部分同步配置")
    print("3. 查看详细的调试信息")
    print("4. 检查后端日志输出")

if __name__ == "__main__":
    main() 