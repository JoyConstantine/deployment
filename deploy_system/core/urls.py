from django.urls import path
from . import views
from . import api
from . import task_views
from . import group_views

urlpatterns = [
    # Web界面路由
    path('', views.root_view, name='root'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('index/', views.index_view, name='index'),
    path('nodes/', views.nodes_view, name='nodes'),
    path('nodes/edit/<int:node_id>/', views.edit_node_view, name='edit_node'),
    path('nodes/delete/<int:node_id>/', views.delete_node_view, name='delete_node'),
    path('nodes/batch/', views.batch_update_nodes_view, name='batch_update_nodes'),
    path('groups/', views.groups_view, name='groups'),
    path('tasks/', views.tasks_view, name='tasks'),
    # 任务管理路由
    path('tasks/create/', task_views.create_task_view, name='create_task'),
    path('tasks/edit/<int:task_id>/', task_views.edit_task_view, name='edit_task'),
    path('tasks/start/<int:task_id>/', task_views.start_task_view, name='start_task'),
    path('tasks/pause/<int:task_id>/', task_views.pause_task_view, name='pause_task'),
    path('tasks/adjust/<int:task_id>/', task_views.adjust_gray_view, name='adjust_gray'),
    path('tasks/detail/<int:task_id>/', task_views.task_detail_view, name='task_detail'),
    path('tasks/delete/<int:task_id>/', task_views.delete_task_view, name='delete_task'),
    # 分组管理路由
    path('groups/create/', group_views.create_group_view, name='create_group'),
    path('groups/edit/<int:group_id>/', group_views.edit_group_view, name='edit_group'),
    path('groups/delete/<int:group_id>/', group_views.delete_group_view, name='delete_group'),
    # API路由
    path('api/node/register/', api.node_register, name='node_register'),
    path('api/node/heartbeat/', api.node_heartbeat, name='node_heartbeat'),
    path('api/node/tasks/', api.get_node_tasks, name='get_node_tasks'),
    path('api/task/status/', api.update_task_status, name='update_task_status'),
    path('api/node/info/', api.get_node_info, name='get_node_info'),
    path('api/node/config-files/', api.get_config_files, name='get_config_files'),
]