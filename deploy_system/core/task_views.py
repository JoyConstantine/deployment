from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import DeployTask, NodeGroup, Node, TaskNode, DeploymentLog
import os
import urllib.request
import shutil
from datetime import datetime

@login_required
def create_task_view(request):
    error_message = ''
    groups = NodeGroup.objects.all()
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            version = request.POST.get('version')
            source_type = request.POST.get('source_type')
            target_directory = request.POST.get('target_directory')
            target_filename = request.POST.get('target_filename')
            full_deployment = request.POST.get('full_deployment', 'off') == 'on'
            
            # 验证版本号格式（简单验证）
            if not version:
                error_message = '版本号不能为空'
                return render(request, 'core/create_task.html', {'groups': groups, 'error_message': error_message})
            
            # 处理文件上传或URL下载
            source_path = ''
            if source_type == 'upload':
                # 处理文件上传
                if 'file' not in request.FILES:
                    error_message = '请选择要上传的文件'
                    return render(request, 'core/create_task.html', {'groups': groups, 'error_message': error_message})
                
                file = request.FILES['file']
                # 创建上传目录
                upload_dir = os.path.join('uploads', datetime.now().strftime('%Y%m%d'))
                os.makedirs(upload_dir, exist_ok=True)
                file_path = os.path.join(upload_dir, file.name)
                
                with open(file_path, 'wb') as f:
                    for chunk in file.chunks():
                        f.write(chunk)
                # 保存相对于uploads目录的路径
                source_path = os.path.relpath(file_path, 'uploads')
            else:
                # 处理URL下载
                url = request.POST.get('url')
                if not url:
                    error_message = '请输入文件URL'
                    return render(request, 'core/create_task.html', {'groups': groups, 'error_message': error_message})
                
                # 对于URL类型，直接保存完整的URL
                source_path = url
            
            # 获取是否为可执行程序
            is_executable = request.POST.get('is_executable', 'off') == 'on'
            # 获取发布后动作
            post_deploy_action = request.POST.get('post_deploy_action', '')
            
            # 处理全量发布逻辑
            if full_deployment:
                # 全量发布：使用用户选择的分组，灰度比例为1.0
                group_ids = request.POST.getlist('groups')
                if not group_ids:
                    error_message = '请选择目标分组'
                    return render(request, 'core/create_task.html', {'groups': groups, 'error_message': error_message})
                gray_ratio = 1.0
            else:
                # 非全量发布：使用用户选择的分组和灰度比例
                group_ids = request.POST.getlist('groups')
                if not group_ids:
                    error_message = '请选择目标分组'
                    return render(request, 'core/create_task.html', {'groups': groups, 'error_message': error_message})
                # 将百分比转换为小数
                gray_ratio = float(request.POST.get('gray_ratio', 10)) / 100
            
            # 获取是否允许降级发布
            allow_downgrade = request.POST.get('allow_downgrade', 'off') == 'on'
            
            # 创建任务
            task = DeployTask.objects.create(
                name=name,
                version=version,
                source_type=source_type,
                source_path=source_path,
                target_directory=target_directory,
                target_filename=target_filename,
                is_executable=is_executable,
                post_deploy_action=post_deploy_action,
                gray_ratio=gray_ratio,
                current_gray_ratio=gray_ratio,
                status='pending',
                created_by=request.user
            )
            
            # 添加目标分组
            for group_id in group_ids:
                group = NodeGroup.objects.get(id=group_id)
                task.groups.add(group)
            
            # 检查版本差异
            nodes = Node.objects.filter(group__id__in=group_ids)
            has_lower_version = False
            for node in nodes:
                if compare_versions(version, node.current_version) < 0:
                    has_lower_version = True
                    break
            
            # 为每个节点创建任务实例
            for node in nodes:
                # 版本校验：只有新版本高于当前版本或允许降级发布才创建任务
                if compare_versions(version, node.current_version) > 0 or allow_downgrade:
                    TaskNode.objects.create(
                        task=task,
                        node=node,
                        status='pending'
                    )
            
            # 如果有节点版本高于发布版本且未勾选允许降级
            if has_lower_version and not allow_downgrade:
                error_message = '部分节点当前版本高于发布版本，建议发布更高版本或勾选允许降级发布'
                return render(request, 'core/create_task.html', {'groups': groups, 'error_message': error_message})
            
            return redirect('tasks')
        except Exception as e:
            error_message = f'创建任务失败: {str(e)}'
    
    return render(request, 'core/create_task.html', {'groups': groups, 'error_message': error_message})

@login_required
def start_task_view(request, task_id):
    try:
        task = DeployTask.objects.get(id=task_id)
        original_status = task.status
        if original_status == 'pending' or original_status == 'paused':
            # 开始或恢复灰度发布
            task.status = 'graying'
            task.save()
            
            # 记录任务启动日志
            action = "任务启动" if original_status == 'pending' else "任务恢复"
            message = f"任务从 {original_status} 状态启动"
            
            # 获取任务关联的所有节点
            nodes = Node.objects.filter(task_nodes__task=task).distinct()
            for node in nodes:
                DeploymentLog.objects.create(
                    task=task,
                    node=node,
                    action=action,
                    message=message,
                    status='info'
                )
            
            # 如果是从pending状态开始，需要选择初始节点
            if original_status == 'pending':
                # 根据灰度比例选择节点
                task_nodes = TaskNode.objects.filter(task=task, status='pending')
                total_nodes = task_nodes.count()
                gray_count = int(total_nodes * task.gray_ratio)
                
                # 选择前gray_count个节点开始执行
                for i, task_node in enumerate(task_nodes):
                    if i < gray_count:
                        task_node.status = 'running'
                        task_node.executed_at = datetime.now()
                        task_node.save()
                        # 记录节点任务启动日志
                        DeploymentLog.objects.create(
                            task=task,
                            node=task_node.node,
                            action="节点任务启动",
                            message=f"开始执行灰度发布，灰度比例: {task.gray_ratio*100:.0f}%",
                            status='info'
                        )
        return redirect('tasks')
    except Exception as e:
        # 处理错误
        return redirect('tasks')

@login_required
def pause_task_view(request, task_id):
    try:
        task = DeployTask.objects.get(id=task_id)
        if task.status == 'graying':
            task.status = 'paused'
            task.save()
            
            # 记录任务暂停日志
            action = "任务暂停"
            message = "任务暂停执行"
            
            # 获取任务关联的所有节点
            nodes = Node.objects.filter(task_nodes__task=task).distinct()
            for node in nodes:
                DeploymentLog.objects.create(
                    task=task,
                    node=node,
                    action=action,
                    message=message,
                    status='info'
                )
        return redirect('tasks')
    except Exception as e:
        # 处理错误
        return redirect('tasks')

@login_required
def adjust_gray_view(request, task_id):
    if request.method == 'POST':
        try:
            task = DeployTask.objects.get(id=task_id)
            old_ratio = task.current_gray_ratio
            # 将百分比转换为小数
            new_ratio = float(request.POST.get('gray_ratio', task.current_gray_ratio * 100)) / 100
            
            if new_ratio > task.current_gray_ratio:
                # 增加灰度比例
                task.current_gray_ratio = new_ratio
                task.save()
                
                # 记录灰度调整日志
                action = "灰度比例调整"
                message = f"灰度比例从 {old_ratio*100:.0f}% 调整到 {new_ratio*100:.0f}%"
                
                # 获取任务关联的所有节点
                nodes = Node.objects.filter(task_nodes__task=task).distinct()
                for node in nodes:
                    DeploymentLog.objects.create(
                        task=task,
                        node=node,
                        action=action,
                        message=message,
                        status='info'
                    )
                
                # 获取所有待执行的节点
                task_nodes = TaskNode.objects.filter(task=task, status='pending')
                total_nodes = TaskNode.objects.filter(task=task).count()
                new_count = int(total_nodes * new_ratio)
                current_running = TaskNode.objects.filter(task=task, status='running').count()
                
                # 需要新增的节点数
                add_count = new_count - current_running
                if add_count > 0:
                    for i, task_node in enumerate(task_nodes[:add_count]):
                        task_node.status = 'running'
                        task_node.executed_at = datetime.now()
                        task_node.save()
                        # 记录节点任务启动日志
                        DeploymentLog.objects.create(
                            task=task,
                            node=task_node.node,
                            action="节点任务启动",
                            message=f"灰度比例调整后开始执行，当前灰度比例: {new_ratio*100:.0f}%",
                            status='info'
                        )
            
            return redirect('tasks')
        except Exception as e:
            # 处理错误
            return redirect('tasks')

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

@login_required
def task_detail_view(request, task_id):
    try:
        task = DeployTask.objects.get(id=task_id)
        # 获取任务关联的所有节点
        task_nodes = TaskNode.objects.filter(task=task)
        # 获取任务的所有日志
        logs = DeploymentLog.objects.filter(task=task).order_by('created_at')
        
        # 计算执行进度
        total_nodes = task_nodes.count()
        completed_nodes = task_nodes.filter(status__in=['success', 'failed']).count()
        progress = (completed_nodes / total_nodes * 100) if total_nodes > 0 else 0
        
        # 计算实际发布比例（基于已完成的节点）
        actual_gray_ratio = (completed_nodes / total_nodes) if total_nodes > 0 else 0
        
        context = {
            'task': task,
            'task_nodes': task_nodes,
            'logs': logs,
            'progress': progress,
            'actual_gray_ratio': actual_gray_ratio,
            'total_nodes': total_nodes,
            'completed_nodes': completed_nodes
        }
        
        return render(request, 'core/task_detail.html', context)
    except DeployTask.DoesNotExist:
        return redirect('tasks')

@login_required
def delete_task_view(request, task_id):
    try:
        task = DeployTask.objects.get(id=task_id)
        task.delete()
    except DeployTask.DoesNotExist:
        pass
    return redirect('tasks')

@login_required
def edit_task_view(request, task_id):
    error_message = ''
    try:
        task = DeployTask.objects.get(id=task_id)
        groups = NodeGroup.objects.all()
        
        if request.method == 'POST':
            try:
                # 获取表单数据
                name = request.POST.get('name')
                version = request.POST.get('version')
                target_directory = request.POST.get('target_directory')
                target_filename = request.POST.get('target_filename')
                full_deployment = request.POST.get('full_deployment', 'off') == 'on'
                
                # 验证版本号格式
                if not version:
                    error_message = '版本号不能为空'
                    return render(request, 'core/edit_task.html', {'task': task, 'groups': groups, 'error_message': error_message})
                
                # 处理全量发布逻辑
                if full_deployment:
                    # 全量发布：使用用户选择的分组，灰度比例为1.0
                    group_ids = request.POST.getlist('groups')
                    if not group_ids:
                        error_message = '请选择目标分组'
                        return render(request, 'core/edit_task.html', {'task': task, 'groups': groups, 'error_message': error_message})
                    gray_ratio = 1.0
                else:
                    # 非全量发布：使用用户选择的分组和灰度比例
                    group_ids = request.POST.getlist('groups')
                    if not group_ids:
                        error_message = '请选择目标分组'
                        return render(request, 'core/edit_task.html', {'task': task, 'groups': groups, 'error_message': error_message})
                    # 将百分比转换为小数
                    gray_ratio = float(request.POST.get('gray_ratio', task.gray_ratio * 100)) / 100
                
                # 获取是否允许降级发布
                allow_downgrade = request.POST.get('allow_downgrade', 'off') == 'on'
                # 获取发布后动作
                post_deploy_action = request.POST.get('post_deploy_action', '')
                
                # 更新任务信息
                task.name = name
                task.version = version
                task.target_directory = target_directory
                task.target_filename = target_filename
                task.post_deploy_action = post_deploy_action
                task.gray_ratio = gray_ratio
                if task.current_gray_ratio < gray_ratio:
                    task.current_gray_ratio = gray_ratio
                task.save()
                
                # 清空现有分组
                task.groups.clear()
                
                # 添加新的分组
                for group_id in group_ids:
                    group = NodeGroup.objects.get(id=group_id)
                    task.groups.add(group)
                
                # 检查版本差异
                nodes = Node.objects.filter(group__id__in=group_ids)
                has_lower_version = False
                for node in nodes:
                    if compare_versions(version, node.current_version) < 0:
                        has_lower_version = True
                        break
                
                # 重新创建任务节点（如果版本高于节点当前版本或允许降级发布）
                TaskNode.objects.filter(task=task).delete()
                for node in nodes:
                    if compare_versions(version, node.current_version) > 0 or allow_downgrade:
                        TaskNode.objects.create(
                            task=task,
                            node=node,
                            status='pending'
                        )
                
                # 如果有节点版本高于发布版本且未勾选允许降级
                if has_lower_version and not allow_downgrade:
                    error_message = '部分节点当前版本高于发布版本，建议发布更高版本或勾选允许降级发布'
                    current_group_ids = [group.id for group in task.groups.all()]
                    return render(request, 'core/edit_task.html', {'task': task, 'groups': groups, 'current_group_ids': current_group_ids, 'error_message': error_message})
                
                return redirect('tasks')
            except Exception as e:
                error_message = f'编辑任务失败: {str(e)}'
        
        # 获取当前任务的分组ID
        current_group_ids = [group.id for group in task.groups.all()]
        
        context = {
            'task': task,
            'groups': groups,
            'current_group_ids': current_group_ids,
            'error_message': error_message
        }
        
        return render(request, 'core/edit_task.html', context)
    except DeployTask.DoesNotExist:
        return redirect('tasks')
