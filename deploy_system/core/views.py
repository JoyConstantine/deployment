from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Node, NodeGroup, DeployTask, TaskNode

# 根路径视图
def root_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    else:
        return redirect('login')

# 登录视图
def login_view(request):
    error_message = ''
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('index')
        else:
            error_message = '用户名或密码错误'
    return render(request, 'core/login.html', {'error_message': error_message})

# 登出视图
def logout_view(request):
    logout(request)
    return redirect('login')

# 首页视图
@login_required
def index_view(request):
    # 统计数据
    total_nodes = Node.objects.count()
    active_nodes = Node.objects.filter(is_active=True).count()
    inactive_nodes = Node.objects.filter(is_active=False).count()
    
    total_tasks = DeployTask.objects.count()
    running_tasks = DeployTask.objects.filter(status__in=['graying', 'paused']).count()
    completed_tasks = DeployTask.objects.filter(status='completed').count()
    
    total_groups = NodeGroup.objects.count()
    if total_groups > 0:
        avg_nodes_per_group = round(Node.objects.count() / total_groups, 1)
    else:
        avg_nodes_per_group = 0
    
    context = {
        'total_nodes': total_nodes,
        'active_nodes': active_nodes,
        'inactive_nodes': inactive_nodes,
        'total_tasks': total_tasks,
        'running_tasks': running_tasks,
        'completed_tasks': completed_tasks,
        'total_groups': total_groups,
        'avg_nodes_per_group': avg_nodes_per_group,
    }
    return render(request, 'core/index.html', context)

# 节点管理视图
@login_required
def nodes_view(request):
    nodes = Node.objects.all()
    groups = NodeGroup.objects.all()
    return render(request, 'core/nodes.html', {'nodes': nodes, 'groups': groups})

# 分组管理视图
@login_required
def groups_view(request):
    groups = NodeGroup.objects.all()
    return render(request, 'core/groups.html', {'groups': groups})

# 任务管理视图
@login_required
def tasks_view(request):
    tasks = DeployTask.objects.all()
    
    # 计算每个任务的实际灰度比例
    for task in tasks:
        task_nodes = TaskNode.objects.filter(task=task)
        total_nodes = task_nodes.count()
        completed_nodes = task_nodes.filter(status__in=['success', 'failed']).count()
        task.actual_gray_ratio = (completed_nodes / total_nodes) if total_nodes > 0 else 0
    
    return render(request, 'core/tasks.html', {'tasks': tasks})

# 节点编辑视图
@login_required
def edit_node_view(request, node_id):
    try:
        node = Node.objects.get(id=node_id)
        groups = NodeGroup.objects.all()
        
        if request.method == 'POST':
            group_id = request.POST.get('group')
            if group_id:
                node.group = NodeGroup.objects.get(id=group_id)
            else:
                node.group = None
            node.save()
            return redirect('nodes')
    except Node.DoesNotExist:
        return redirect('nodes')
    
    return render(request, 'core/edit_node.html', {'node': node, 'groups': groups})

# 节点删除视图
@login_required
def delete_node_view(request, node_id):
    try:
        node = Node.objects.get(id=node_id)
        node.delete()
    except Node.DoesNotExist:
        pass
    return redirect('nodes')

# 批量更新节点视图
@login_required
def batch_update_nodes_view(request):
    if request.method == 'POST':
        node_ids = request.POST.getlist('node_ids')
        action = request.POST.get('action')
        
        if not node_ids:
            return redirect('nodes')
        
        if action == 'assign_group':
            group_id = request.POST.get('group')
            if group_id:
                try:
                    group = NodeGroup.objects.get(id=group_id)
                    Node.objects.filter(id__in=node_ids).update(group=group)
                except NodeGroup.DoesNotExist:
                    pass
        elif action == 'delete':
            Node.objects.filter(id__in=node_ids).delete()
    
    return redirect('nodes')
