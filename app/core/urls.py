# from django.urls import path, include
# from django.contrib.auth import views as auth_views
# from django.contrib.auth import logout
# from django.shortcuts import redirect
# from rest_framework.routers import DefaultRouter
# from . import views


# def logout_view(request):
#     logout(request)
#     return redirect('login')


# router = DefaultRouter()
# router.register(r'backups', views.BackupViewSet, basename='backup')

# urlpatterns = [
#     # Main pages
#     path('', views.index, name='index'),
#     path('api/', views.api, name='api'),
    
#     # Backups
#     path('backups/', views.backups_list, name='backup_list'),
#     path('backups/<uuid:pk>/', views.backup_detail, name='backup_detail'),

#     # TargetSystems CRUD
#     path('target-systems/', views.system_settings, name='target_system_list'),
#     path('target-systems/create/', views.system_create, name='target_system_create'),
#     path('target-systems/<int:pk>/', views.system_detail, name='target_system_detail'),
#     path('target-systems/<int:pk>/edit/', views.system_edit, name='target_system_edit'),
#     path('target-systems/<int:pk>/delete/', views.system_delete, name='target_system_delete'),

#     # Hosts CRUD
#     path('hosts/', views.servers, name='host_list'),
#     path('hosts/create/', views.host_create, name='host_create'),
#     path('hosts/<int:pk>/', views.host_detail, name='host_detail'),
#     path('hosts/<int:pk>/edit/', views.host_edit, name='host_edit'),
#     path('hosts/<int:pk>/delete/', views.host_delete, name='host_delete'),

#     # REST API (ViewSet)
#     path('api/', include(router.urls)),

#     # Authentication
#     path('login/', auth_views.LoginView.as_view(
#         template_name='registration/login.html'
#     ), name='login'),
# ]

from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout
from django.shortcuts import redirect
from rest_framework.routers import DefaultRouter
from . import views


def logout_view(request):
    logout(request)
    return redirect('login')


# REST API Router
router = DefaultRouter()
router.register(r'system-types', views.SystemTypeViewSet, basename='systemtype')
router.register(r'environments', views.EnvironmentViewSet, basename='environment')
router.register(r'backup-tools', views.BackupToolViewSet, basename='backuptools')
router.register(r'target-systems', views.TargetSystemViewSet, basename='targetsystem')
router.register(r'backup-configurations', views.BackupConfigurationViewSet, basename='backupconfiguration')
router.register(r'backup-operations', views.BackupOperationViewSet, basename='backupoperation')


urlpatterns = [
    # Main pages
    path('', views.index, name='index'),
    path('api/', views.api, name='api'),
    
    # Backup Operations
    path('operations/', views.operations_list, name='operation_list'),
    path('operations/<int:pk>/', views.operation_detail, name='operation_detail'),
    
    # TargetSystems CRUD
    path('target-systems/', views.system_settings, name='target_system_list'),
    path('target-systems/create/', views.system_create, name='target_system_create'),
    path('target-systems/<int:pk>/', views.system_detail, name='target_system_detail'),
    path('target-systems/<int:pk>/edit/', views.system_edit, name='target_system_edit'),
    path('target-systems/<int:pk>/delete/', views.system_delete, name='target_system_delete'),
    
    # Backup Configurations CRUD
    path('configurations/', views.configuration_list, name='configuration_list'),
    path('configurations/create/', views.configuration_create, name='configuration_create'),
    path('configurations/<int:pk>/', views.configuration_detail, name='configuration_detail'),
    path('configurations/<int:pk>/edit/', views.configuration_edit, name='configuration_edit'),
    path('configurations/<int:pk>/delete/', views.configuration_delete, name='configuration_delete'),
    
    # REST API (ViewSet)
    path('api/v1/', include(router.urls)),
    
    # Authentication
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html'
    ), name='login'),
    path('logout/', logout_view, name='logout'),
]