# Orbyss

🧩 Orbyss is a Django-based workspace and task collaboration app built to help teams manage workspaces, invite members, assign tasks, and track progress in a clean, modern interface.

---

## 🚀 What Orbyss Does

Orbyss gives teams a simple way to:

- Create and manage workspaces
- Invite workspace members
- Create tasks with deadlines, priority, and assignment
- View tasks assigned to users
- Complete tasks with comments
- Track completed vs active tasks
- Provide workspace owners with insights into workspace activities

---

## 🎯 Key Features

### Workspace Management
- Workspace creation and editing
- Member invitation and removal
- Workspace-specific task management

### Task Management
- Task creation with name, description, priority, deadline, and assignee
- Assign tasks to workspace members or self-assign
- Completed tasks remain stored and are never deleted automatically
- Task completion requires a completion comment
- Workspace owner views completed tasks and comments
- Task detail page with task metadata and completion history

### User Profile
- Profile page shows user details
- Workspace count, assigned task count, completed tasks, and remaining tasks
- Recent tasks and recent workspaces overview

### Security Improvements
- Login error messages are displayed clearly
- Brute-force protection via login attempt throttling
- Strong password validation
- CSRF protection through Django templates
- Safe task access checks for owners and assignees

---

## 🧱 What’s Included

This project includes:

- `Orbyss/dashboard/` — dashboard app for workspaces, tasks, members, and profile pages
- `Orbyss/Login/` — authentication views, registration, and login templates
- `Orbyss/Orbyss/` — main Django project settings, URLs, and WSGI/ASGI configuration
- `README.md` — this project guide
- `agent.md` — detailed implementation and security notes

---

## 🛠️ Setup Instructions

1. Open the project folder.
2. Activate your virtual environment:
   ```powershell
   .\.venv\Scripts\Activate
   ```
3. Install dependencies if needed:
   ```powershell
   pip install -r requirements.txt
   ```
4. Run migrations:
   ```powershell
   python Orbyss\manage.py makemigrations
   python Orbyss\manage.py migrate
   ```
5. Start the development server:
   ```powershell
   python Orbyss\manage.py runserver
   ```
6. Open the app in your browser:
   ```text
   http://127.0.0.1:8000/
   ```

---

## 🧠 How the App Works

### Dashboard
The dashboard lets workspace owners create and manage workspaces. From there, owners can invite members and add tasks to workspaces.

### Task Flow
1. Create a task with name, description, priority, deadline, and assigned member.
2. Assigned users can view their active tasks.
3. Users mark tasks complete and add a completion comment.
4. Workspace owners can view completed tasks along with comments.

### Profile Page
The profile page summarizes:
- personal user information
- workspaces created
- tasks assigned
- completed tasks
- remaining tasks
- recent workspace activity

---

## 📌 Important Notes

- Completed tasks are not deleted automatically.
- Task completion records `completed_at`, `completed_by`, and a `completion_comment`.
- Workspace deletion cascades and removes associated tasks.
- The app is built with Django’s authentication, ORM, templates, and cache features.

---

## ✅ UI Improvements

Updated task pages to use:
- rounded buttons
- pill-style status tabs
- improved action button spacing
- cleaner completion and navigation controls

---

## 🧪 Recommended Testing

Test the following flows:

- Register and login
- Create a workspace
- Add members to the workspace
- Create tasks and assign them
- View active and completed tasks
- Mark a task complete with a completion comment
- Open task detail and confirm completion information
- Visit profile page and confirm stats

---

## 📝 Project Status

This is a working Django app with core workspace and task management features implemented. It is designed for further enhancement with collaboration, real-time updates, and richer analytics.

---

## 📎 File References

- `Orbyss/dashboard/models.py` — workspace and task models
- `Orbyss/dashboard/views.py` — dashboard, task, and profile logic
- `Orbyss/dashboard/templates/` — HTML templates for pages
- `Orbyss/Login/views.py` — login and register logic
- `Orbyss/Login/templates/login.html` — login UI
- `agent.md` — implementation notes and security summary

---

## 🌟 Final Thought
Orbyss is built to help users picture a focused workspace where teams manage projects, assign work, and close tasks with accountability. The interface is designed to be clean, modern, and easy to use.
