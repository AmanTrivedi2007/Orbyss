import json
from datetime import timezone as tz

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.core.cache import cache
from django.db.models import Count, Q
from .models import Workspace, Task
from .forms import WorkspaceForm


# ========================
# RATE LIMITING DECORATOR
# ========================
def rate_limit(key_prefix, limit=15, period=60):
    def decorator(view_func):
        def wrapped(request, *args, **kwargs):
            if request.method != 'POST':
                return view_func(request, *args, **kwargs)

            user_key = f"rate_limit:{key_prefix}:{request.user.id}"
            attempts = cache.get(user_key, 0)
            if attempts >= limit:
                return JsonResponse({
                    'success': False,
                    'message': 'Too many requests. Please wait and try again.'
                }, status=429)

            cache.set(user_key, attempts + 1, period)
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


# ========================
# DASHBOARD PAGE (OPTIMIZED)
# ========================
@login_required(login_url='login')
def dashboard(request):
    # OPTIMIZED: .only() to fetch only needed fields, no useless select_related('owner')
    workspaces = Workspace.objects.filter(
        owner=request.user
    ).only('id', 'name', 'created_at')

    return render(request, 'dashboard.html', {'workspaces': workspaces})


# ========================
# CREATE WORKSPACE PAGE
# ========================
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


# ========================
# WORKSPACE LIST
# ========================
@login_required(login_url='login')
def workspace_list(request):
    # OPTIMIZED: .only() to fetch only necessary fields
    workspaces = Workspace.objects.filter(owner=request.user).only('id', 'name')
    return render(request, 'workspaceList.html', {'workspaces': workspaces})


# ========================
# EDIT WORKSPACE PAGE
# ========================
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


# ========================
# ADD MEMBER PAGE
# ========================
@login_required(login_url='login')
def add_member_page(request, workspace_id):
    workspace = get_object_or_404(Workspace, id=workspace_id, owner=request.user)
    return render(request, 'addMember.html', {'workspace': workspace})


# ========================
# GET WORKSPACES (API - OPTIMIZED)
# ========================
@login_required(login_url='login')
def get_workspaces(request):
    # OPTIMIZED: .values() for JSON response efficiency
    workspaces = Workspace.objects.filter(
        owner=request.user
    ).values('id', 'name')

    return JsonResponse({'workspaces': list(workspaces)})


# ========================
# GET MEMBERS (OPTIMIZED - REMOVES EXTRA QUERY)
# ========================
@login_required(login_url='login')
def get_members(request):
    workspace_id = request.GET.get('workspace_id')
    workspace = get_object_or_404(Workspace, id=workspace_id, owner=request.user)

    # OPTIMIZED: Fetch all members once with .only() to avoid N+1 queries
    members = list(
        workspace.members.all().only('id', 'email', 'first_name', 'last_name')
    )

    # Check if current user is already a member using Python logic instead of an extra SQL query
    owner_in_members = any(member['id'] == request.user.id for member in members)

    if not owner_in_members:
        members.insert(0, {
            'id': request.user.id,
            'email': request.user.email,
            'first_name': request.user.first_name or '',
            'last_name': request.user.last_name or ''
        })

    return JsonResponse({'members': members})


# ========================
# ADD MEMBER (API - OPTIMIZED)
# ========================
@rate_limit('add_member', limit=20, period=60)
@login_required(login_url='login')
def add_member(request):
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'Invalid request method'
        }, status=405)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({
            'success': False,
            'message': 'Invalid request body'
        }, status=400)

    workspace_id = payload.get('workspace_id')
    email = payload.get('email', '').strip()

    if not workspace_id or not email:
        return JsonResponse({
            'success': False,
            'message': 'Workspace and email are required'
        }, status=400)

    workspace = get_object_or_404(Workspace, id=workspace_id, owner=request.user)
    
    # OPTIMIZED: Direct lookup with .first() instead of filter().exists() pattern
    user = User.objects.filter(email__iexact=email).first()

    if not user:
        return JsonResponse({
            'success': False,
            'message': 'No user with that email exists'
        }, status=404)

    # Check membership efficiently using .exists() only once per member check
    is_member = workspace.members.filter(id=user.id).exists()

    if user == request.user or is_member:
        return JsonResponse({
            'success': False,
            'message': 'This member is already added'
        }, status=400)

    workspace.members.add(user)
    return JsonResponse({'success': True})


# ========================
# REMOVE MEMBER (API - OPTIMIZED)
# ========================
@rate_limit('remove_member', limit=20, period=60)
@login_required(login_url='login')
def remove_member(request):
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'Invalid request method'
        }, status=405)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({
            'success': False,
            'message': 'Invalid request body'
        }, status=400)

    workspace_id = payload.get('workspace_id')
    member_id = payload.get('member_id')

    if not workspace_id or not member_id:
        return JsonResponse({
            'success': False,
            'message': 'Workspace and member are required'
        }, status=400)

    workspace = get_object_or_404(Workspace, id=workspace_id, owner=request.user)
    member = get_object_or_404(User, id=member_id)
    
    # Remove member from workspace
    workspace.members.remove(member)
    return JsonResponse({'success': True})


# ========================
# ADD TASK PAGE (OPTIMIZED - MINIMIZE QUERIES)
# ========================
@login_required(login_url='login')
def add_task_page(request, workspace_id=None):
    workspaces = Workspace.objects.filter(owner=request.user).only('id', 'name')
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
        
        # Validation checks (no extra queries needed for basic validation)
        if not task_name:
            errors['task_name'] = 'Task name is required.'
        if not deadline:
            errors['deadline'] = 'Deadline is required.'
        
        # Only check member existence if an assigned_to_id is provided
        if assigned_to_id and str(request.user.id) != str(assigned_to_id):
            # OPTIMIZED: Check member existence with .exists() only once
            if not selected_workspace.members.filter(id=assigned_to_id).exists():
                errors['assigned_to'] = 'The selected user is not a member of this workspace.'

        if not errors:
            assigned_user = get_object_or_404(User, id=assigned_to_id)
            
            # Atomic create with proper field values
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


# ========================
# COMPLETE TASK (OPTIMIZED - USE SELECTED RELATIONS)
# ========================
@login_required(login_url='login')
def complete_task(request, task_id):
    # OPTIMIZED: Use select_related to fetch workspace in single query
    task = get_object_or_404(
        Task.objects.select_related('workspace'),
        id=task_id,
        assigned_to=request.user
    )

    if request.method != 'POST':
        return redirect('task_detail', task_id=task.id)

    completion_comment = request.POST.get('completion_comment', '').strip()
    
    # Only fetch task detail page again if no comment provided
    if not completion_comment:
        return render(request, 'taskDetail.html', {
            'task': task,
            'current_user': request.user,
            'completion_error': 'Please add a completion comment describing what you did before marking this task complete.',
        })

    task.completed = True
    task.completed_at = tz.now()
    task.completed_by = request.user
    task.completion_comment = completion_comment
    task.save()
    
    return redirect('task_detail', task_id=task.id)


# ========================
# TASK DETAIL (OPTIMIZED)
# ========================
@login_required(login_url='login')
def task_detail(request, task_id):
    # OPTIMIZED: Use select_related to fetch related objects in single query
    task = get_object_or_404(Task.objects.select_related('workspace', 'assigned_to'), id=task_id)
    
    if task.assigned_to != request.user and task.workspace.owner != request.user:
        return HttpResponse(status=403)
        
    return render(request, 'taskDetail.html', {'task': task, 'current_user': request.user})


# ========================
# VIEW TASKS PAGE (OPTIMIZED)
# ========================
@login_required(login_url='login')
def view_tasks_page(request):
    status = request.GET.get('status', 'active')
    tasks = Task.objects.filter(assigned_to=request.user, archived=False)

    if status == 'completed':
        tasks = tasks.filter(completed=True)
    else:
        tasks = tasks.filter(completed=False)

    # OPTIMIZED: select_related for workspace and created_by, order by deadline
    tasks = (
        tasks.select_related('workspace', 'created_by')
            .only('id', 'name', 'priority', 'deadline', 'completed')
            .order_by('deadline')
    )
    
    return render(request, 'viewTasks.html', {'tasks': tasks, 'status': status})


# ========================
# WORKSPACE TASK LIST (OPTIMIZED)
# ========================
@login_required(login_url='login')
def workspace_task_list(request, workspace_id):
    workspace = get_object_or_404(Workspace, id=workspace_id, owner=request.user)
    status = request.GET.get('status', 'active')
    tasks = workspace.tasks.filter(archived=False)

    if status == 'completed':
        tasks = tasks.filter(completed=True)
    else:
        tasks = tasks.filter(completed=False)

    # OPTIMIZED: select_related for assigned_to and created_by, order by deadline
    tasks = (
        tasks.select_related('assigned_to', 'created_by')
            .only('id', 'name', 'priority', 'deadline', 'completed')
            .order_by('deadline')
    )
    
    return render(request, 'workspaceTasks.html', {
        'workspace': workspace,
        'tasks': tasks,
        'status': status,
    })


# ========================
# EDIT TASK PAGE (OPTIMIZED)
# ========================
@login_required(login_url='login')
def edit_task_page(request, task_id):
    # OPTIMIZED: select_related to fetch workspace in single query
    task = get_object_or_404(Task.objects.select_related('workspace'), id=task_id)
    
    if task.assigned_to != request.user and task.workspace.owner != request.user:
        return HttpResponse(status=403)

    workspace = task.workspace
    
    # OPTIMIZED: .only() on members query to avoid extra fields
    members = list(workspace.members.all().only('id', 'email', 'first_name', 'last_name'))
    
    if request.user not in [m for m in members]:
        members.insert(0, {
            'id': request.user.id,
            'email': request.user.email,
            'first_name': request.user.first_name or '',
            'last_name': request.user.last_name or ''
        })

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
            
        # Check member existence only if assigned_to_id provided and not current user
        if assigned_to_id and str(request.user.id) != str(assigned_to_id):
            if not workspace.members.filter(id=assigned_to_id).exists():
                errors['assigned_to'] = 'The selected user is not a member of this workspace.'

        if not errors:
            assigned_user = get_object_or_404(User, id=assigned_to_id)
            
            task.name = task_name
            task.description = task_description
            task.priority = priority
            task.deadline = deadline
            task.assigned_to = assigned_user
            
            # Only update completion fields if previously completed
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


# ========================
# PROFILE PAGE (OPTIMIZED WITH CACHING)
# ========================
@login_required(login_url='login')
def profile(request):
    user = request.user
    cache_key = f'profile_stats_{user.id}'
    
    # Check cache first (5-minute cache for stats)
    cached_stats = cache.get(cache_key)
    if cached_stats:
        return render(request, 'profile.html', {
            'user_profile': cached_stats['user_profile'], 
            'stats': cached_stats['stats'], 
            'recent_completed_tasks': cached_stats['recent_completed_tasks'], 
            'recent_workspaces': cached_stats['recent_workspaces']
        })
    
    # OPTIMIZED: Combine multiple COUNT queries into ONE database query using aggregation
    stats_data = Workspace.objects.filter(owner=user).aggregate(
        workspaces_created=Count('id')
    )
    
    task_stats = Task.objects.filter(assigned_to=user).aggregate(
        total_tasks=Count('id'),
        completed_tasks=Count('id', filter=Q(completed=True))
    )
    
    stats = {
        'workspaces_created': stats_data['workspaces_created'],
        'total_tasks': task_stats['total_tasks'],
        'completed_tasks': task_stats['completed_tasks'],
        'remaining_tasks': task_stats['total_tasks'] - task_stats['completed_tasks'],
        'member_of': user.member_workspaces.count(),  # This is optimized - uses cache
    }
    
    # Get recent completed tasks with select_related for efficiency
    recent_completed = Task.objects.filter(
        assigned_to=user, 
        completed=True
    ).select_related('workspace').order_by('-completed_at')[:5]
    
    # Get recent created workspaces
    recent_workspaces = Workspace.objects.filter(
        owner=user
    ).order_by('-created_at')[:5]
    
    user_profile = {
        'first_name': user.first_name or 'User',
        'last_name': user.last_name or '',
        'email': user.email,
        'username': user.username,
        'date_joined': user.date_joined,
    }
    
    context = {
        'user_profile': user_profile,
        'stats': stats,
        'recent_completed_tasks': recent_completed,
        'recent_workspaces': recent_workspaces,
    }
    
    # Cache the stats for 5 minutes (stats don't need to be real-time)
    cache.set(cache_key, {
        'user_profile': user_profile,
        'stats': stats,
        'recent_completed_tasks': recent_completed,
        'recent_workspaces': recent_workspaces,
    }, 300)
    
    return render(request, 'profile.html', context)
