#!/usr/bin/env python3
import requests
import os

# 测试文件下载功能
def test_file_download():
    server_url = 'http://192.168.123.152:8000'
    
    # 测试从服务器下载文件
    test_path = '20230101/test.txt'
    
    try:
        url = f"{server_url}/static/{test_path}"
        print(f"测试下载: {url}")
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print(f"✓ 下载成功，文件大小: {len(response.content)} bytes")
            print(f"文件内容: {response.text}")
        else:
            print(f"✗ 下载失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
    except Exception as e:
        print(f"✗ 下载错误: {e}")

if __name__ == '__main__':
    test_file_download()
