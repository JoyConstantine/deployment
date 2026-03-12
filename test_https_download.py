#!/usr/bin/env python3
import os
import sys
import shutil
from deploy_client import DeployClient

# 测试 HTTPS 下载功能
def test_https_download():
    # 创建客户端实例
    server_url = 'http://192.168.123.152:8000'
    client = DeployClient(server_url)
    
    # 测试 HTTPS URL 下载
    print("测试 HTTPS URL 下载...")
    test_url = 'https://spring.zhenxcloud.cn/edge_client'
    test_dir = os.path.join(os.getcwd(), 'test_https')
    
    # 清理测试目录
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    
    # 创建测试目录
    os.makedirs(test_dir, exist_ok=True)
    
    # 下载文件
    save_path = os.path.join(test_dir, 'edge_client')
    print(f"下载文件: {test_url} -> {save_path}")
    result = client.download_file(test_url, save_path)
    print(f"文件下载结果: {'成功' if result else '失败'}")
    
    # 检查下载的文件
    print("\n检查下载的文件:")
    if os.path.exists(save_path):
        print(f"文件存在，大小: {os.path.getsize(save_path)} bytes")
    else:
        print("文件不存在")
    
    # 清理测试目录
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        print("\n测试目录已清理")

if __name__ == '__main__':
    test_https_download()
