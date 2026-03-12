#!/usr/bin/env python3
import os
import sys
import shutil
from deploy_client import DeployClient

# 测试配置文件下载功能
def test_config_download():
    # 创建客户端实例
    server_url = 'http://192.168.123.152:8000'
    client = DeployClient(server_url)
    
    # 测试获取配置文件列表
    print("测试获取配置文件列表...")
    config_files = client.get_config_files()
    print(f"获取到 {len(config_files)} 个配置文件:")
    for file in config_files:
        print(f"  - {file.get('name')}: {file.get('path')}")
    
    # 测试下载配置文件
    print("\n测试下载配置文件...")
    test_dir = os.path.join(os.getcwd(), 'test_config')
    
    # 清理测试目录
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    
    # 创建测试目录
    os.makedirs(test_dir, exist_ok=True)
    
    # 下载配置文件（第一次）
    print("\n第一次下载配置文件:")
    result = client.download_config_files(test_dir)
    print(f"配置文件下载结果: {'成功' if result else '失败'}")
    
    # 检查下载的文件
    print("\n检查下载的文件:")
    if os.path.exists(test_dir):
        downloaded_files = os.listdir(test_dir)
        print(f"下载目录中的文件: {downloaded_files}")
        for file in downloaded_files:
            file_path = os.path.join(test_dir, file)
            if os.path.isfile(file_path):
                print(f"  - {file}: {os.path.getsize(file_path)} bytes")
                # 显示文件权限
                print(f"  - 权限: {oct(os.stat(file_path).st_mode)[-4:]}")
    else:
        print("下载目录不存在")
    
    # 再次下载配置文件（测试备份和权限保持）
    print("\n第二次下载配置文件（测试备份和权限保持）:")
    result = client.download_config_files(test_dir)
    print(f"配置文件下载结果: {'成功' if result else '失败'}")
    
    # 检查备份目录
    print("\n检查备份目录:")
    backup_dir = os.path.join(os.getcwd(), 'backup')
    if os.path.exists(backup_dir):
        print("备份目录存在")
        for root, dirs, files in os.walk(backup_dir):
            for file in files:
                print(f"  - {os.path.join(root, file)}")
    else:
        print("备份目录不存在")
    
    # 清理测试目录
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        print("\n测试目录已清理")
    
    # 清理备份目录
    if os.path.exists(backup_dir):
        shutil.rmtree(backup_dir)
        print("备份目录已清理")

if __name__ == '__main__':
    test_config_download()
