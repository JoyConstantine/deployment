#!/usr/bin/env python3
import requests
import os

# 测试文件下载功能
def test_file_download():
    server_url = 'http://192.168.123.152:8000'
    
    # 测试从服务器下载文件
    test_files = [
        # 测试上传文件
        'uploads/20230101/test.txt',
        # 测试URL下载文件
        'downloads/20230101/test.txt'
    ]
    
    for file_path in test_files:
        try:
            url = f"{server_url}/static/{file_path}"
            print(f"测试下载: {url}")
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                print(f"✓ 下载成功，文件大小: {len(response.content)} bytes")
                # 保存到本地
                local_path = f"test_{os.path.basename(file_path)}"
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                print(f"✓ 保存到本地: {local_path}")
            else:
                print(f"✗ 下载失败，状态码: {response.status_code}")
        except Exception as e:
            print(f"✗ 下载错误: {e}")

if __name__ == '__main__':
    test_file_download()
