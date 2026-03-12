import os
import sys
import django

# 切换到项目目录
project_dir = 'd:/data/code/upgrade/deployment/deploy_system'
os.chdir(project_dir)

# 将项目目录添加到 Python 路径
sys.path.append(project_dir)

# 设置 Django 设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deploy_system.settings')

# 初始化 Django 环境
django.setup()

# 导入模型
from core.models import DeployTask, TaskNode

# 查询灰度中任务
tasks = DeployTask.objects.filter(status='graying')
print('灰度中任务:', tasks.count())

for task in tasks:
    print(f'任务ID: {task.id}, 名称: {task.name}, 灰度比例: {task.current_gray_ratio*100:.0f}%, 状态: {task.status}')
    task_nodes = TaskNode.objects.filter(task=task)
    print(f'  总节点数: {task_nodes.count()}')
    print(f'  待执行: {task_nodes.filter(status="pending").count()}')
    print(f'  执行中: {task_nodes.filter(status="running").count()}')
    print(f'  成功: {task_nodes.filter(status="success").count()}')
    print(f'  失败: {task_nodes.filter(status="failed").count()}')
