from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout
from django.shortcuts import redirect
from rest_framework.routers import DefaultRouter
from . import views

def logout_view(request):
    logout(request)
    return redirect('login')

router = DefaultRouter()
router.register(r'backups', views.BackupViewSet, basename='backup')

urlpatterns = [
    path('', include(router.urls)),
    
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', logout_view, name='logout'),
]
