from django.shortcuts import render,redirect
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib.auth import login
from .forms import RegisterForm
from .models import Profile


def login_page(request):

    if request.method=="POST":

        email=request.POST.get("email")
        password=request.POST.get("password")

        user=authenticate(
            username=email,
            password=password
        )

        if user:

            login(request,user)

            return redirect(
                "dashboard"
            )

    return render(
        request,
        "login.html"
    )


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

def dashboard(request):
    return render(
        request,
        "dashboard.html"
    )