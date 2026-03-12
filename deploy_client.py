#!/usr/bin/env python3
import os
import sys
import time
import requests
import json
import socket
import uuid
import subprocess
import shutil
from datetime import datetime
import logging

# 配置日志
log_file = 'deploy_client.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

class DeployClient:
    def __init__(self, server_url, node_id=None):
        self.server_url = server_url
        self.node_id = node_id or self.generate_node_id()
        self.hostname = socket.gethostname()
        self.ip_address = self.get_ip_address()
        self.heartbeat_interval = 30  # 心跳间隔（秒）
        self.task_check_interval = 10  # 任务检查间隔（秒）
        # 设置备份目录为当前目录的 backup 子目录
        self.backup_dir = os.path.join(os.getcwd(), 'backup')
        
    def generate_node_id(self):
        """生成唯一的节点ID并存储到本地文件"""
        # 尝试从本地文件读取节点ID
        id_file = '/etc/deploy_node_id'
        if os.path.exists(id_file):
            try:
                with open(id_file, 'r') as f:
                    node_id = f.read().strip()
                    if node_id:
                        return node_id
            except Exception as e:
                logging.error(f"读取节点ID文件失败: {e}")
        
        # 生成新的节点ID
        node_id = str(uuid.uuid4())
        
        # 存储节点ID到本地文件
        try:
            os.makedirs(os.path.dirname(id_file), exist_ok=True)
            with open(id_file, 'w') as f:
                f.write(node_id)
        except Exception as e:
            logging.error(f"存储节点ID文件失败: {e}")
        
        return node_id
    
    def get_ip_address(self):
        """获取节点IP地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception as e:
            logging.error(f"获取IP地址失败: {e}")
            return '127.0.0.1'
    
    def register(self):
        """向服务器注册节点"""
        try:
            url = f"{self.server_url}/api/node/register/"
            data = {
                'node_id': self.node_id,
                'hostname': self.hostname,
                'ip_address': self.ip_address
            }
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            if result.get('status') == 'success':
                logging.info(f"节点注册成功: {self.node_id}")
                return True
            else:
                logging.error(f"节点注册失败: {result.get('message')}")
                return False
        except Exception as e:
            logging.error(f"注册失败: {e}")
            return False
    
    def send_heartbeat(self):
        """发送心跳包"""
        try:
            url = f"{self.server_url}/api/node/heartbeat/"
            data = {'node_id': self.node_id}
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            if result.get('status') == 'success':
                logging.debug("心跳发送成功")
                return True
            else:
                logging.error(f"心跳发送失败: {result.get('message')}")
                return False
        except Exception as e:
            logging.error(f"心跳发送失败: {e}")
            return False
    
    def get_tasks(self):
        """获取待执行任务"""
        try:
            url = f"{self.server_url}/api/node/tasks/"
            data = {'node_id': self.node_id}
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            if result.get('status') == 'success':
                return result.get('tasks', [])
            else:
                logging.error(f"获取任务失败: {result.get('message')}")
                return []
        except Exception as e:
            logging.error(f"获取任务失败: {e}")
            return []
    
    def update_task_status(self, task_id, status, error_message=''):
        """更新任务状态"""
        try:
            url = f"{self.server_url}/api/task/status/"
            data = {
                'task_id': task_id,
                'node_id': self.node_id,
                'status': status,
                'error_message': error_message
            }
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            if result.get('status') == 'success':
                logging.debug(f"任务状态更新成功: {task_id} - {status}")
                return True
            else:
                logging.error(f"任务状态更新失败: {result.get('message')}")
                return False
        except Exception as e:
            logging.error(f"任务状态更新失败: {e}")
            return False
    
    def backup_file(self, file_path, app_name):
        """备份文件"""
        try:
            # 创建备份目录
            backup_app_dir = os.path.join(self.backup_dir, app_name)
            os.makedirs(backup_app_dir, exist_ok=True)
            
            if os.path.exists(file_path):
                # 生成备份文件名
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                backup_file_name = f"{os.path.basename(file_path)}_{timestamp}"
                backup_file_path = os.path.join(backup_app_dir, backup_file_name)
                
                # 复制文件到备份目录
                shutil.copy2(file_path, backup_file_path)
                logging.info(f"文件备份成功: {file_path} -> {backup_file_path}")
                return True
            return False
        except Exception as e:
            logging.error(f"文件备份失败: {e}")
            return False
    
    def download_file(self, url, save_path):
        """下载文件"""
        try:
            # 创建保存目录
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # 尝试使用 requests 库下载
            try:
                # 禁用 SSL 验证，解决 SSL 模块不可用的问题
                response = requests.get(url, stream=True, timeout=30, verify=False)
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logging.info(f"文件下载成功: {url} -> {save_path}")
                return True
            except Exception as e:
                logging.warning(f"使用 requests 下载失败: {e}")
                # 尝试使用 urllib 库下载
                try:
                    import urllib.request
                    # 尝试不使用 SSL 上下文
                    try:
                        with urllib.request.urlopen(url, timeout=30) as response:
                            with open(save_path, 'wb') as f:
                                f.write(response.read())
                        logging.info(f"文件下载成功 (urllib): {url} -> {save_path}")
                        return True
                    except Exception as e3:
                        logging.warning(f"使用 urllib 下载失败: {e3}")
                        # 尝试使用系统命令下载
                        try:
                            logging.info(f"尝试使用系统命令下载: {url}")
                            # 根据操作系统选择不同的命令
                            if os.name == 'nt':  # Windows
                                # 使用 PowerShell 命令下载
                                cmd = f"powershell -Command (New-Object System.Net.WebClient).DownloadFile('{url}', '{save_path}')"
                            else:  # Linux/Mac
                                # 使用 wget 或 curl 命令下载
                                if shutil.which('wget'):
                                    cmd = f"wget -O '{save_path}' '{url}'"
                                elif shutil.which('curl'):
                                    cmd = f"curl -o '{save_path}' '{url}'"
                                else:
                                    raise Exception("系统中没有可用的下载工具")
                            
                            # 执行命令
                            subprocess.run(cmd, shell=True, check=True, timeout=300)
                            logging.info(f"文件下载成功 (系统命令): {url} -> {save_path}")
                            return True
                        except Exception as e4:
                            logging.error(f"使用系统命令下载失败: {e4}")
                            raise
                except Exception as e2:
                    logging.error(f"使用 urllib 下载失败: {e2}")
                    raise
        except Exception as e:
            logging.error(f"文件下载失败: {e}")
            # 检查是否是 SSL 相关错误
            if "SSL" in str(e) or "_ssl" in str(e):
                logging.error("系统缺少 SSL 模块，无法下载 HTTPS URL。请考虑以下解决方案:")
                logging.error("1. 安装 Python 的 SSL 模块")
                logging.error("2. 使用 HTTP URL 替代 HTTPS URL")
                logging.error("3. 在系统中安装 wget 或 curl 命令行工具")
            return False
    
    def execute_task(self, task):
        """执行任务"""
        task_id = task.get('task_id')
        name = task.get('name')
        version = task.get('version')
        source_type = task.get('source_type')
        source_path = task.get('source_path')
        target_directory = task.get('target_directory')
        target_filename = task.get('target_filename')
        is_executable = task.get('is_executable', False)
        post_deploy_action = task.get('post_deploy_action', None)
        
        try:
            logging.info(f"开始执行任务: {task_id} - {name} v{version}")
            logging.info(f"目标目录: {target_directory}")
            if post_deploy_action:
                logging.info(f"发布后动作: {post_deploy_action}")
            
            # 更新任务状态为运行中
            logging.info("更新任务状态为运行中...")
            self.update_task_status(task_id, 'running')
            
            # 确保目标目录存在
            logging.info(f"确保目标目录存在: {target_directory}")
            os.makedirs(target_directory, exist_ok=True)
            logging.info(f"目标目录准备就绪: {target_directory}")
            
            # 处理文件来源
            # 确保只提取文件名，不管source_path中是否包含路径
            original_file_name = os.path.basename(source_path.replace('\\', '/'))
            # 使用目标文件名字（如果提供），否则使用原文件名
            final_file_name = target_filename if target_filename else original_file_name
            local_file_path = os.path.join('/tmp', f"deploy_task_{task_id}_{original_file_name}")
            logging.info(f"临时文件路径: {local_file_path}")
            
            if source_type == 'upload':
                # 从服务器下载文件
                file_url = f"{self.server_url}/static/{source_path}"
                logging.info(f"从服务器下载文件: {file_url}")
                if not self.download_file(file_url, local_file_path):
                    raise Exception("文件下载失败")
            else:
                # 直接使用URL下载
                logging.info(f"从URL下载文件: {source_path}")
                if not self.download_file(source_path, local_file_path):
                    raise Exception("文件下载失败")
            
            # 检查文件是否下载成功
            if not os.path.exists(local_file_path):
                raise Exception("文件下载后不存在")
            logging.info(f"文件下载成功，大小: {os.path.getsize(local_file_path)} bytes")
            
            # 备份目标文件
            target_file_path = os.path.join(target_directory, final_file_name)
            logging.info(f"目标文件路径: {target_file_path}")
            if os.path.exists(target_file_path):
                logging.info("备份目标文件...")
                if self.backup_file(target_file_path, name):
                    logging.info("文件备份成功")
                else:
                    logging.warning("文件备份失败，但继续执行")
            
            # 保存目标文件的权限（如果存在）
            original_permissions = None
            if os.path.exists(target_file_path):
                original_permissions = os.stat(target_file_path).st_mode
                logging.info(f"保存目标文件权限: {oct(original_permissions)}")
            
            # 移动文件到目标目录
            logging.info(f"移动文件到目标目录: {local_file_path} -> {target_file_path}")
            shutil.move(local_file_path, target_file_path)
            logging.info("文件移动成功")
            
            # 恢复目标文件的权限（如果存在）
            if original_permissions:
                try:
                    os.chmod(target_file_path, original_permissions)
                    logging.info(f"恢复目标文件权限: {oct(original_permissions)}")
                except Exception as e:
                    logging.warning(f"恢复文件权限失败: {e}")
            # 设置可执行权限（如果需要）
            elif is_executable or target_file_path.endswith(('.sh', '.bin', '.exe')):
                logging.info(f"设置文件可执行权限: {target_file_path}")
                os.chmod(target_file_path, 0o755)
                logging.info("权限设置成功")
            
            # 验证文件是否成功覆盖
            if not os.path.exists(target_file_path):
                raise Exception("文件覆盖失败")
            logging.info(f"文件覆盖成功，最终路径: {target_file_path}")
            
            # 执行发布后动作
            action_result = ""
            if post_deploy_action:
                logging.info(f"执行发布后动作: {post_deploy_action}")
                try:
                    # 执行命令
                    result = subprocess.run(post_deploy_action, shell=True, capture_output=True, text=True, timeout=60)
                    action_result = f"命令执行结果: 退出码 {result.returncode}\n标准输出: {result.stdout}\n标准错误: {result.stderr}"
                    logging.info(f"发布后动作执行成功: {action_result}")
                except Exception as e:
                    action_result = f"发布后动作执行失败: {str(e)}"
                    logging.error(action_result)
                    # 即使发布后动作失败，也不影响任务状态
            
            # 更新任务状态为成功，包含发布后动作结果
            logging.info("更新任务状态为成功...")
            success_message = f"部署成功"
            if action_result:
                success_message += f"\n{action_result}"
            self.update_task_status(task_id, 'success', success_message)
            logging.info(f"任务执行成功: {task_id}")
            if action_result:
                logging.info(f"发布后动作结果: {action_result}")
        except Exception as e:
            error_message = str(e)
            logging.error(f"任务执行失败: {error_message}")
            self.update_task_status(task_id, 'failed', error_message)
    
    def get_config_files(self):
        """获取服务器配置文件列表"""
        try:
            url = f"{self.server_url}/api/node/config-files/"
            data = {'node_id': self.node_id}
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            if result.get('status') == 'success':
                return result.get('config_files', [])
            else:
                logging.error(f"获取配置文件列表失败: {result.get('message')}")
                return []
        except Exception as e:
            logging.error(f"获取配置文件列表失败: {e}")
            return []
    
    def download_config_files(self, target_directory):
        """下载服务器配置文件到指定目录"""
        try:
            # 获取配置文件列表
            config_files = self.get_config_files()
            logging.info(f"获取到 {len(config_files)} 个配置文件")
            
            # 确保目标目录存在
            os.makedirs(target_directory, exist_ok=True)
            
            # 下载每个配置文件
            for config_file in config_files:
                file_name = config_file.get('name')
                file_path = config_file.get('path')
                
                # 构建下载URL
                download_url = f"{self.server_url}/static/{file_path}"
                save_path = os.path.join(target_directory, file_name)
                
                # 保存原文件的权限
                original_permissions = None
                if os.path.exists(save_path):
                    logging.info(f"目标文件已存在，执行备份: {save_path}")
                    # 保存原文件权限
                    original_permissions = os.stat(save_path).st_mode
                    # 使用 backup_file 方法备份文件
                    # 这里使用文件名作为应用名
                    if self.backup_file(save_path, file_name):
                        logging.info(f"文件备份成功: {file_name}")
                    else:
                        logging.warning(f"文件备份失败，但继续执行: {file_name}")
                
                # 下载文件
                logging.info(f"下载配置文件: {download_url} -> {save_path}")
                if self.download_file(download_url, save_path):
                    logging.info(f"配置文件下载成功: {file_name}")
                    # 恢复原文件的权限
                    if original_permissions:
                        try:
                            os.chmod(save_path, original_permissions)
                            logging.info(f"文件权限已恢复: {file_name}")
                        except Exception as e:
                            logging.warning(f"恢复文件权限失败: {e}")
                else:
                    logging.error(f"配置文件下载失败: {file_name}")
            
            return True
        except Exception as e:
            logging.error(f"下载配置文件失败: {e}")
            return False
    
    def run(self):
        """主运行循环"""
        logging.info(f"启动部署客户端，节点ID: {self.node_id}")
        
        # 注册节点
        while not self.register():
            logging.info("注册失败，5秒后重试...")
            time.sleep(5)
        
        # 主循环
        last_heartbeat = time.time()
        last_task_check = time.time()
        last_config_download = time.time()
        config_download_interval = 3600  # 配置文件下载间隔（秒）
        
        while True:
            current_time = time.time()
            
            # 发送心跳
            if current_time - last_heartbeat >= self.heartbeat_interval:
                logging.info("发送心跳包...")
                result = self.send_heartbeat()
                logging.info(f"心跳发送结果: {'成功' if result else '失败'}")
                last_heartbeat = current_time
            
            # 检查任务
            if current_time - last_task_check >= self.task_check_interval:
                logging.info("检查任务...")
                tasks = self.get_tasks()
                logging.info(f"获取到 {len(tasks)} 个任务")
                for task in tasks:
                    logging.info(f"执行任务: {task.get('name')} v{task.get('version')}")
                    self.execute_task(task)
                last_task_check = current_time
            
            # 定期下载配置文件
            if current_time - last_config_download >= config_download_interval:
                logging.info("下载配置文件...")
                # 默认下载到当前目录的 config 子目录
                default_config_dir = os.path.join(os.getcwd(), 'config')
                self.download_config_files(default_config_dir)
                last_config_download = current_time
            
            time.sleep(1)

if __name__ == '__main__':
    # 默认服务器URL
    server_url = 'http://192.168.123.154:5000'
    
    # 从命令行参数获取服务器URL
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    
    # 创建并运行客户端
    client = DeployClient(server_url)
    client.run()
