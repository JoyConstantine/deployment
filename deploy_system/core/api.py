from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Node, DeployTask, TaskNode, VersionRecord, DeploymentLog
from datetime import datetime
import os
import shutil
import subprocess

@csrf_exempt
def node_register(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            node_id = data.get('node_id')
            hostname = data.get('hostname')
            ip_address = data.get('ip_address')
            
            if not node_id or not hostname or not ip_address:
                return JsonResponse({'status': 'error', 'message': 'Missing required fields'})
            
            # 检查节点是否已存在
            node, created = Node.objects.get_or_create(
                node_id=node_id,
                defaults={
                    'hostname': hostname,
                    'ip_address': ip_address,
                    'is_active': True,
                    'last_heartbeat': datetime.now()
                }
            )
            
            if not created:
                # 更新现有节点信息
                node.hostname = hostname
                node.ip_address = ip_address
                node.is_active = True
                node.last_heartbeat = datetime.now()
                node.save()
            
            return JsonResponse({'status': 'success', 'node_id': node_id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
def node_heartbeat(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            node_id = data.get('node_id')
            
            if not node_id:
                return JsonResponse({'status': 'error', 'message': 'Missing node_id'})
            
            try:
                node = Node.objects.get(node_id=node_id)
                node.last_heartbeat = datetime.now()
                node.is_active = True
                node.save()
                return JsonResponse({'status': 'success'})
            except Node.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Node not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
def get_node_tasks(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            node_id = data.get('node_id')
            
            if not node_id:
                return JsonResponse({'status': 'error', 'message': 'Missing node_id'})
            
            try:
                node = Node.objects.get(node_id=node_id)
                # 获取该节点的待执行任务和正在执行的任务
                task_nodes = TaskNode.objects.filter(node=node, status__in=['pending', 'running'])
                tasks = []
                for task_node in task_nodes:
                    task = task_node.task
                    tasks.append({
                        'task_id': task.id,
                        'name': task.name,
                        'version': task.version,
                        'source_type': task.source_type,
                        'source_path': task.source_path,
                        'target_directory': task.target_directory,
                        'target_filename': task.target_filename,
                        'is_executable': task.is_executable,
                        'post_deploy_action': task.post_deploy_action
                    })
                return JsonResponse({'status': 'success', 'tasks': tasks})
            except Node.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Node not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
def update_task_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            task_id = data.get('task_id')
            node_id = data.get('node_id')
            status = data.get('status')
            error_message = data.get('error_message', '')
            
            if not task_id or not node_id or not status:
                return JsonResponse({'status': 'error', 'message': 'Missing required fields'})
            
            try:
                node = Node.objects.get(node_id=node_id)
                task = DeployTask.objects.get(id=task_id)
                task_node = TaskNode.objects.get(task=task, node=node)
                
                task_node.status = status
                task_node.completed_at = datetime.now()
                if error_message:
                    task_node.error_message = error_message
                task_node.save()
                
                # 记录任务状态变更日志
                action = f"任务状态变更"
                message = f"任务状态从 {task_node.status} 变更为 {status}"
                if status == 'success':
                    message += f"，版本更新为 {task.version}"
                elif status == 'failed':
                    message += f"，错误信息：{error_message}"
                
                DeploymentLog.objects.create(
                    task=task,
                    node=node,
                    action=action,
                    message=message,
                    status='success' if status == 'success' else 'error' if status == 'failed' else 'info'
                )
                
                # 如果任务成功，更新节点版本
                if status == 'success':
                    node.current_version = task.version
                    node.save()
                    # 创建版本记录
                    VersionRecord.objects.create(
                        node=node,
                        version=task.version,
                        task=task
                    )
                    # 记录版本更新日志
                    DeploymentLog.objects.create(
                        task=task,
                        node=node,
                        action="版本更新",
                        message=f"节点版本更新为 {task.version}",
                        status='success'
                    )
                
                # 检查任务是否所有节点都已完成
                all_completed = TaskNode.objects.filter(task=task).exclude(status__in=['success', 'failed']).count() == 0
                if all_completed:
                    task.status = 'completed'
                    task.save()
                    # 记录任务完成日志
                    DeploymentLog.objects.create(
                        task=task,
                        node=node,
                        action="任务完成",
                        message="所有节点任务执行完成",
                        status='info'
                    )
                
                return JsonResponse({'status': 'success'})
            except (Node.DoesNotExist, DeployTask.DoesNotExist, TaskNode.DoesNotExist):
                return JsonResponse({'status': 'error', 'message': 'Task or node not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
def get_node_info(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            node_id = data.get('node_id')
            
            if not node_id:
                return JsonResponse({'status': 'error', 'message': 'Missing node_id'})
            
            try:
                node = Node.objects.get(node_id=node_id)
                return JsonResponse({
                    'status': 'success',
                    'node_info': {
                        'node_id': node.node_id,
                        'hostname': node.hostname,
                        'ip_address': node.ip_address,
                        'current_version': node.current_version,
                        'last_heartbeat': node.last_heartbeat.strftime('%Y-%m-%d %H:%M:%S')
                    }
                })
            except Node.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Node not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
def get_config_files(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            node_id = data.get('node_id')
            
            if not node_id:
                return JsonResponse({'status': 'error', 'message': 'Missing node_id'})
            
            # 检查节点是否存在（可选）
            # 即使节点不存在，也返回配置文件列表
            # try:
            #     node = Node.objects.get(node_id=node_id)
            # except Node.DoesNotExist:
            #     return JsonResponse({'status': 'error', 'message': 'Node not found'})
            
            # 获取配置文件列表
            config_files = []
            # 这里可以根据实际需求从数据库或文件系统获取配置文件列表
            # 暂时返回一个示例列表
            config_files = [
                {'name': 'config.json', 'path': 'config/config.json'},
                {'name': 'settings.ini', 'path': 'config/settings.ini'}
            ]
            
            return JsonResponse({'status': 'success', 'config_files': config_files})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
