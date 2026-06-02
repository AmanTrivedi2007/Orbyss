from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.core.exceptions import SuspiciousOperation
from .forms import RegisterForm
from .models import Profile


def rate_limit_login(request, limit=5, period=900):
    """Rate limit login attempts: max 5 per 15 minutes per IP"""
    ip = get_client_ip(request)
    cache_key = f"login_attempts:{ip}"
    attempts = cache.get(cache_key, 0)
    
    if attempts >= limit:
        return True  # Rate limited
    
    cache.set(cache_key, attempts + 1, period)
    return False  # Not rate limited


def get_client_ip(request):
    """Get client IP address safely"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip or 'unknown'


def login_page(request):
    context = {}
    
    if request.method == "POST":
        # Check rate limiting
        if rate_limit_login(request):
            context['error'] = 'Too many login attempts. Please try again in 15 minutes.'
            return render(request, "login.html", context)
        
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        
        # Validate input
        if not email or not password:
            context['error'] = 'Please provide both email and password.'
            return render(request, "login.html", context)
        
        # Authenticate
        user = authenticate(username=email, password=password)
        
        if user:
            login(request, user)
            return redirect("/dashboard/")
        else:
            # Generic error message for security
            context['error'] = 'Invalid email or password.'
    
    return render(request, "login.html", context)


def register(request):

    if request.method=="POST":

        form=RegisterForm(request.POST)

        if form.is_valid():

            user=User.objects.create_user(

                username=form.cleaned_data["email"],

                email=form.cleaned_data["email"],

                password=form.cleaned_data["password"],

                first_name=form.cleaned_data["first_name"],

                last_name=form.cleaned_data["last_name"]

            )

            Profile.objects.create(

                user=user,

                company=form.cleaned_data["company"]

            )

            return redirect(
                "login_page"
            )

    else:

        form=RegisterForm()


    return render(

        request,

        "reg.html",

        {"form":form}

    )


def logout_page(request):
    logout(request)
    return redirect('index_page')

