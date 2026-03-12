from django.db import models
from django.contrib.auth.models import User
from datetime import datetime

class NodeGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Node(models.Model):
    node_id = models.CharField(max_length=100, unique=True)
    hostname = models.CharField(max_length=255)
    ip_address = models.CharField(max_length=50)
    group = models.ForeignKey(NodeGroup, on_delete=models.SET_NULL, null=True, related_name='nodes')
    current_version = models.CharField(max_length=50, default='0.0.0')
    last_heartbeat = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.hostname} ({self.ip_address})"

class DeployTask(models.Model):
    STATUS_CHOICES = [
        ('pending', '待发布'),
        ('graying', '灰度中'),
        ('paused', '暂停'),
        ('completed', '完成'),
        ('failed', '失败'),
    ]
    
    name = models.CharField(max_length=255)
    version = models.CharField(max_length=50)
    source_type = models.CharField(max_length=20, choices=[('upload', '本地上传'), ('url', 'URL下载')])
    source_path = models.CharField(max_length=500)
    target_directory = models.CharField(max_length=500)
    target_filename = models.CharField(max_length=255, blank=True, null=True)  # 目标文件名字
    is_executable = models.BooleanField(default=False)  # 是否为可执行程序
    post_deploy_action = models.CharField(max_length=500, blank=True, null=True)  # 发布后动作
    groups = models.ManyToManyField(NodeGroup, related_name='tasks')
    gray_ratio = models.FloatField(default=0.1)  # 初始灰度比例
    current_gray_ratio = models.FloatField(default=0.1)  # 当前灰度比例
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} v{self.version}"

class TaskNode(models.Model):
    task = models.ForeignKey(DeployTask, on_delete=models.CASCADE, related_name='task_nodes')
    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='task_nodes')
    status = models.CharField(max_length=20, choices=[('pending', '待执行'), ('running', '执行中'), ('success', '成功'), ('failed', '失败')], default='pending')
    executed_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        unique_together = ('task', 'node')

class VersionRecord(models.Model):
    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='version_records')
    version = models.CharField(max_length=50)
    task = models.ForeignKey(DeployTask, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.node.hostname} v{self.version}"

class DeploymentLog(models.Model):
    task = models.ForeignKey(DeployTask, on_delete=models.CASCADE, related_name='logs')
    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=100)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=[('info', '信息'), ('success', '成功'), ('error', '错误')])
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.node.hostname} - {self.action} - {self.status}"
