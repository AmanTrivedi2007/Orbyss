from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name="dashboard_page"),
    path('create/', views.create_workspace, name="create_workspace"),
    path('list/', views.workspace_list, name="workspace_list"),
    path('edit/<int:workspace_id>/', views.edit_workspace, name="edit_workspace"),
    path('task/add/', views.add_task_page, name="add_task_page"),
    path('workspace/<int:workspace_id>/task/add/', views.add_task_page, name="add_task_for_workspace"),
    path('tasks/view/', views.view_tasks_page, name="view_tasks_page"),
    path('workspace/<int:workspace_id>/members/', views.add_member_page, name="add_member_page"),
    path('workspace/get/', views.get_workspaces, name="get_workspaces"),
    path('workspace/members/list/', views.get_members, name="get_members"),
    path('workspace/members/add/', views.add_member, name="add_member"),
    path('workspace/members/remove/', views.remove_member, name="remove_member"),
    path('workspace/<int:workspace_id>/tasks/', views.workspace_task_list, name='workspace_task_list'),
    path('tasks/<int:task_id>/edit/', views.edit_task_page, name='edit_task_page'),
    path('tasks/<int:task_id>/complete/', views.complete_task, name='complete_task'),
    path('tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    path('profile/', views.profile, name='dashboard_profile'),
]
