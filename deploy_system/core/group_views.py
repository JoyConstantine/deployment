from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import NodeGroup

@login_required
def create_group_view(request):
    error_message = ''
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            description = request.POST.get('description')
            
            if not name:
                error_message = '分组名称不能为空'
                return render(request, 'core/create_group.html', {'error_message': error_message})
            
            # 检查分组名称是否已存在
            if NodeGroup.objects.filter(name=name).exists():
                error_message = '分组名称已存在'
                return render(request, 'core/create_group.html', {'error_message': error_message})
            
            # 创建分组
            NodeGroup.objects.create(
                name=name,
                description=description
            )
            
            return redirect('groups')
        except Exception as e:
            error_message = f'创建分组失败: {str(e)}'
    
    return render(request, 'core/create_group.html', {'error_message': error_message})

@login_required
def edit_group_view(request, group_id):
    error_message = ''
    
    try:
        group = NodeGroup.objects.get(id=group_id)
        
        if request.method == 'POST':
            name = request.POST.get('name')
            description = request.POST.get('description')
            
            if not name:
                error_message = '分组名称不能为空'
                return render(request, 'core/edit_group.html', {'group': group, 'error_message': error_message})
            
            # 检查分组名称是否已存在（排除当前分组）
            if NodeGroup.objects.filter(name=name).exclude(id=group_id).exists():
                error_message = '分组名称已存在'
                return render(request, 'core/edit_group.html', {'group': group, 'error_message': error_message})
            
            # 更新分组
            group.name = name
            group.description = description
            group.save()
            
            return redirect('groups')
    except NodeGroup.DoesNotExist:
        error_message = '分组不存在'
        return redirect('groups')
    except Exception as e:
        error_message = f'编辑分组失败: {str(e)}'
    
    return render(request, 'core/edit_group.html', {'group': group, 'error_message': error_message})

@login_required
def delete_group_view(request, group_id):
    try:
        group = NodeGroup.objects.get(id=group_id)
        # 检查是否有节点属于该分组
        if group.nodes.exists():
            # 可以选择将节点移到其他分组或设置为未分组
            # 这里简单处理，直接删除分组（实际应用中应该有更合理的处理）
            pass
        group.delete()
    except Exception as e:
        pass
    
    return redirect('groups')
