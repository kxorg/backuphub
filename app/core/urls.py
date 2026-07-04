from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout
from django.shortcuts import redirect
from rest_framework.routers import DefaultRouter
from . import views

# Logout handler via GET request
def logout_view(request):
    logout(request)
    return redirect('login')

# Только BackupViewSet
router = DefaultRouter()
router.register(r'backups', views.BackupViewSet, basename='backup')

urlpatterns = [
    # API для Backups
    path('', include(router.urls)),
    
    # Аутентификация
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html'
    ), name='login'),
    
    path('logout/', views.logout_view, name='logout'),
]