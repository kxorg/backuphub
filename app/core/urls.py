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
    # Main pages
    path('', views.index, name='index'),
    path('api/', views.api, name='api'),

    # Backups
    path('backups/', views.backups_list, name='backup_list'),
    path('backups/<uuid:pk>/', views.backup_detail, name='backup_detail'),

    # TargetSystems CRUD
    path('target-systems/', views.system_settings, name='target_system_list'),
    path('target-systems/create/', views.system_create, name='target_system_create'),
    path('target-systems/<int:pk>/', views.system_detail, name='target_system_detail'),
    path('target-systems/<int:pk>/edit/', views.system_edit, name='target_system_edit'),
    path('target-systems/<int:pk>/delete/', views.system_delete, name='target_system_delete'),

    # Hosts CRUD
    path('hosts/', views.servers, name='host_list'),
    path('hosts/create/', views.host_create, name='host_create'),
    path('hosts/<int:pk>/', views.host_detail, name='host_detail'),
    path('hosts/<int:pk>/edit/', views.host_edit, name='host_edit'),
    path('hosts/<int:pk>/delete/', views.host_delete, name='host_delete'),

    # REST API (ViewSet)
    path('api/', include(router.urls)),

    # Authentication
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html'
    ), name='login'),
]