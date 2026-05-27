from django.urls import path,include
from . import views

urlpatterns = [
    path('login/',views.login_page,name='login_page'),
    path('registration/',views.register,name='registration_page'),
]