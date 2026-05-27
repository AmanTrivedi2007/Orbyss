from django.http import HttpResponse
from django.shortcuts import render

def index(request):
    return render(request,'index.html')

def term(request):
    return render(request,'term.html')

def privacy(request):
    return render(request,'privacy.html')