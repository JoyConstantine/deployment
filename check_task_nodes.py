import os
import sys
import django

# 版本比较函数
def compare_versions(v1, v2):
    """比较两个版本号，返回1（v1>v2）, 0（v1=v2）, -1（v1<v2）"""
    # 移除v前缀
    v1 = v1.lstrip('v')
    v2 = v2.lstrip('v')
    
    # 分割版本号
    v1_parts = list(map(int, v1.split('.')))
    v2_parts = list(map(int, v2.split('.')))
    
    # 补全长度
    max_len = max(len(v1_parts), len(v2_parts))
    v1_parts.extend([0] * (max_len - len(v1_parts)))
    v2_parts.extend([0] * (max_len - len(v2_parts)))
    
    # 逐位比较
    for i in range(max_len):
        if v1_parts[i] > v2_parts[i]:
            return 1
        elif v1_parts[i] < v2_parts[i]:
            return -1
    return 0

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
from core.models import DeployTask, TaskNode, Node, NodeGroup

# 查询灰度中任务
tasks = DeployTask.objects.filter(status='graying')
print('灰度中任务:', tasks.count())

for task in tasks:
    print(f'任务ID: {task.id}, 名称: {task.name}, 版本: {task.version}, 灰度比例: {task.current_gray_ratio*100:.0f}%, 状态: {task.status}')
    
    # 检查任务关联的分组
    groups = task.groups.all()
    print(f'  关联分组数: {groups.count()}')
    for group in groups:
        print(f'  分组: {group.name}')
        # 检查分组中的节点
        nodes_in_group = group.nodes.filter(is_active=True)
        print(f'    分组中活跃节点数: {nodes_in_group.count()}')
        for node in nodes_in_group:
            print(f'    节点: {node.hostname} ({node.ip_address}), 当前版本: {node.current_version}')
            print(f'    版本比较结果: {compare_versions(task.version, node.current_version)}')
    
    # 检查任务节点
    task_nodes = TaskNode.objects.filter(task=task)
    print(f'  任务节点数: {task_nodes.count()}')
