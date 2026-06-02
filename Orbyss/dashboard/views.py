import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.core.cache import cache
from django.utils import timezone

from .models import Workspace, Task
from .forms import WorkspaceForm


def rate_limit(key_prefix, limit=15, period=60):
    def decorator(view_func):
        def wrapped(request, *args, **kwargs):
            if request.method != 'POST':
                return view_func(request, *args, **kwargs)

            user_key = f"rate_limit:{key_prefix}:{request.user.id}"
            attempts = cache.get(user_key, 0)
            if attempts >= limit:
                return JsonResponse({'success': False, 'message': 'Too many requests. Please wait and try again.'}, status=429)

            cache.set(user_key, attempts + 1, period)
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


@login_required(login_url='login')
def dashboard(request):
    workspaces = Workspace.objects.filter(owner=request.user)
    return render(request, 'dashboard.html', {'workspaces': workspaces})

@login_required(login_url='login')
def create_workspace(request):
    if request.method == 'POST':
        form = WorkspaceForm(request.POST)
        if form.is_valid():
            workspace = form.save(commit=False)
            workspace.owner = request.user
            workspace.save()
            return redirect('dashboard_page')
    else:
        form = WorkspaceForm()
    return render(request, 'workspaceCreate.html', {'form': form})

@login_required(login_url='login')
def workspace_list(request):
    workspaces = Workspace.objects.filter(owner=request.user)
    return render(request, 'workspaceList.html', {'workspaces': workspaces})

@login_required(login_url='login')
def edit_workspace(request, workspace_id):
    workspace = get_object_or_404(Workspace, id=workspace_id, owner=request.user)
    if request.method == 'POST':
        form = WorkspaceForm(request.POST, instance=workspace)
        if form.is_valid():
            form.save()
            return redirect('dashboard_page')
    else:
        form = WorkspaceForm(instance=workspace)
    return render(request, 'workSpaceEdit.html', {'form': form, 'workspace': workspace})

@login_required(login_url='login')
def add_member_page(request, workspace_id):
    workspace = get_object_or_404(Workspace, id=workspace_id, owner=request.user)
    return render(request, 'addMember.html', {'workspace': workspace})

@login_required(login_url='login')
def get_workspaces(request):
    workspaces = Workspace.objects.filter(owner=request.user).values('id', 'name')
    return JsonResponse({'workspaces': list(workspaces)})

@login_required(login_url='login')
def get_members(request):
    workspace_id = request.GET.get('workspace_id')
    workspace = get_object_or_404(Workspace, id=workspace_id, owner=request.user)
    members = list(workspace.members.all().values('id', 'email', 'first_name', 'last_name'))

    if request.user.id not in [member['id'] for member in members]:
        members.insert(0, {
            'id': request.user.id,
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
        })

    return JsonResponse({'members': members})

@rate_limit('add_member', limit=20, period=60)
@login_required(login_url='login')
def add_member(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'success': False, 'message': 'Invalid request body'}, status=400)

    workspace_id = payload.get('workspace_id')
    email = payload.get('email', '').strip()

    if not workspace_id or not email:
        return JsonResponse({'success': False, 'message': 'Workspace and email are required'}, status=400)

    workspace = get_object_or_404(Workspace, id=workspace_id, owner=request.user)
    user = User.objects.filter(email__iexact=email).first()

    if not user:
        return JsonResponse({'success': False, 'message': 'No user with that email exists'}, status=404)

    if user == request.user or workspace.members.filter(id=user.id).exists():
        return JsonResponse({'success': False, 'message': 'This member is already added'}, status=400)

    workspace.members.add(user)
    return JsonResponse({'success': True})

@rate_limit('remove_member', limit=20, period=60)
@login_required(login_url='login')
def remove_member(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'success': False, 'message': 'Invalid request body'}, status=400)

    workspace_id = payload.get('workspace_id')
    member_id = payload.get('member_id')

    if not workspace_id or not member_id:
        return JsonResponse({'success': False, 'message': 'Workspace and member are required'}, status=400)

    workspace = get_object_or_404(Workspace, id=workspace_id, owner=request.user)
    member = get_object_or_404(User, id=member_id)
    workspace.members.remove(member)
    return JsonResponse({'success': True})

@login_required(login_url='login')
def add_task_page(request, workspace_id=None):
    workspaces = Workspace.objects.filter(owner=request.user)
    selected_workspace = None

    if workspace_id:
        selected_workspace = get_object_or_404(Workspace, id=workspace_id, owner=request.user)

    if request.method == 'POST':
        workspace_id_post = request.POST.get('workspace_id') or workspace_id
        selected_workspace = get_object_or_404(Workspace, id=workspace_id_post, owner=request.user)
        task_name = request.POST.get('task_name', '').strip()
        task_description = request.POST.get('task_description', '').strip()
        priority = request.POST.get('priority', 'medium')
        deadline = request.POST.get('deadline')
        assigned_to_id = request.POST.get('assigned_to')

        errors = {}
        if not task_name:
            errors['task_name'] = 'Task name is required.'
        if not deadline:
            errors['deadline'] = 'Deadline is required.'
        if not assigned_to_id:
            errors['assigned_to'] = 'Please assign the task to a workspace member or yourself.'

        if assigned_to_id and not selected_workspace.members.filter(id=assigned_to_id).exists() and str(request.user.id) != str(assigned_to_id):
            errors['assigned_to'] = 'The selected user is not a member of this workspace.'

        if not errors:
            assigned_user = get_object_or_404(User, id=assigned_to_id)
            Task.objects.create(
                name=task_name,
                description=task_description,
                priority=priority,
                deadline=deadline,
                workspace=selected_workspace,
                assigned_to=assigned_user,
                created_by=request.user,
            )
            return render(request, 'addTask.html', {
                'workspaces': workspaces,
                'selected_workspace': selected_workspace,
                'success_message': 'Task created successfully.',
            })

        return render(request, 'addTask.html', {
            'workspaces': workspaces,
            'selected_workspace': selected_workspace,
            'errors': errors,
            'form_data': request.POST,
        })

    return render(request, 'addTask.html', {
        'workspaces': workspaces,
        'selected_workspace': selected_workspace,
    })

@login_required(login_url='login')
def complete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, assigned_to=request.user)
    if request.method != 'POST':
        return redirect('task_detail', task_id=task.id)

    completion_comment = request.POST.get('completion_comment', '').strip()
    if not completion_comment:
        return render(request, 'taskDetail.html', {
            'task': task,
            'completion_error': 'Please add a completion comment describing what you did before marking this task complete.',
        })

    task.completed = True
    task.completed_at = timezone.now()
    task.completed_by = request.user
    task.completion_comment = completion_comment
    task.save()
    return redirect('task_detail', task_id=task.id)

@login_required(login_url='login')
def task_detail(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if task.assigned_to != request.user and task.workspace.owner != request.user:
        return HttpResponse(status=403)
    return render(request, 'taskDetail.html', {'task': task, 'current_user': request.user})

@login_required(login_url='login')
def view_tasks_page(request):
    status = request.GET.get('status', 'active')
    tasks = Task.objects.filter(assigned_to=request.user, archived=False)

    if status == 'completed':
        tasks = tasks.filter(completed=True)
    else:
        tasks = tasks.filter(completed=False)

    tasks = tasks.select_related('workspace', 'assigned_to', 'created_by').order_by('deadline')
    return render(request, 'viewTasks.html', {'tasks': tasks, 'status': status})

@login_required(login_url='login')
def workspace_task_list(request, workspace_id):
    workspace = get_object_or_404(Workspace, id=workspace_id, owner=request.user)
    status = request.GET.get('status', 'active')
    tasks = workspace.tasks.filter(archived=False)

    if status == 'completed':
        tasks = tasks.filter(completed=True)
    else:
        tasks = tasks.filter(completed=False)

    tasks = tasks.select_related('assigned_to', 'created_by').order_by('deadline')
    return render(request, 'workspaceTasks.html', {
        'workspace': workspace,
        'tasks': tasks,
        'status': status,
    })

@login_required(login_url='login')
def edit_task_page(request, task_id):
    task = get_object_or_404(Task, id=task_id, workspace__owner=request.user)
    workspace = task.workspace
    members = list(workspace.members.all())
    if request.user not in members:
        members.insert(0, request.user)

    if request.method == 'POST':
        task_name = request.POST.get('task_name', '').strip()
        task_description = request.POST.get('task_description', '').strip()
        priority = request.POST.get('priority', 'medium')
        deadline = request.POST.get('deadline')
        assigned_to_id = request.POST.get('assigned_to')
        completion_comment = request.POST.get('completion_comment', '').strip()

        errors = {}
        if not task_name:
            errors['task_name'] = 'Task name is required.'
        if not deadline:
            errors['deadline'] = 'Deadline is required.'
        if not assigned_to_id:
            errors['assigned_to'] = 'Please assign the task to a workspace member or yourself.'
        elif not workspace.members.filter(id=assigned_to_id).exists() and str(request.user.id) != str(assigned_to_id):
            errors['assigned_to'] = 'The selected user is not a member of this workspace.'

        if not errors:
            assigned_user = get_object_or_404(User, id=assigned_to_id)
            task.name = task_name
            task.description = task_description
            task.priority = priority
            task.deadline = deadline
            task.assigned_to = assigned_user
            if task.completed and completion_comment:
                task.completion_comment = completion_comment
            task.save()
            return render(request, 'editTask.html', {
                'task': task,
                'workspace': workspace,
                'members': members,
                'success_message': 'Task updated successfully.',
            })

        return render(request, 'editTask.html', {
            'task': task,
            'workspace': workspace,
            'members': members,
            'errors': errors,
            'form_data': request.POST,
        })

    return render(request, 'editTask.html', {
        'task': task,
        'workspace': workspace,
        'members': members,
    })

@login_required(login_url='login')
def profile(request):
    user = request.user
    
    # Get user stats
    workspaces_count = Workspace.objects.filter(owner=user).count()
    total_tasks = Task.objects.filter(assigned_to=user).count()
    completed_tasks = Task.objects.filter(assigned_to=user, completed=True).count()
    remaining_tasks = total_tasks - completed_tasks
    member_of_workspaces = user.member_workspaces.count()
    
    # Get recent completed tasks
    recent_completed = Task.objects.filter(
        assigned_to=user, 
        completed=True
    ).select_related('workspace').order_by('-completed_at')[:5]
    
    # Get recent created workspaces
    recent_workspaces = Workspace.objects.filter(
        owner=user
    ).order_by('-created_at')[:5]
    
    context = {
        'user_profile': {
            'first_name': user.first_name or 'User',
            'last_name': user.last_name or '',
            'email': user.email,
            'username': user.username,
            'date_joined': user.date_joined,
        },
        'stats': {
            'workspaces_created': workspaces_count,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'remaining_tasks': remaining_tasks,
            'member_of': member_of_workspaces,
        },
        'recent_completed_tasks': recent_completed,
        'recent_workspaces': recent_workspaces,
    }
    
    return render(request, 'profile.html', context)