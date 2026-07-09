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
# router = DefaultRouter()
# router.register(r'system-types', views.SystemTypeViewSet, basename='systemtype')
# router.register(r'environments', views.EnvironmentViewSet, basename='environment')
# router.register(r'backup-tools', views.BackupToolViewSet, basename='backuptools')
# router.register(r'target-systems', views.TargetSystemViewSet, basename='targetsystem')
# router.register(r'backup-configurations', views.BackupConfigurationViewSet, basename='backupconfiguration')
# router.register(r'backup-operations', views.BackupOperationViewSet, basename='backupoperation')


urlpatterns = [
    # Main pages
    path('', views.index, name='index'),
    # path('api/', views.api, name='api'),
    
    # Backup Operations
    path('backup-operations/', views.BackupOperationListView.as_view(), name='backup_operation_list'),
    path('backup-operations/<int:pk>/', views.BackupOperationDetailView.as_view(), name='backup_operation_detail'),

    # TargetSystems CRUD
    path('target-systems/', views.TargetSystemListView.as_view(), name='target_system_list'),
    path('target-systems/create/', views.TargetSystemCreateView.as_view(), name='target_system_create'),
    path('target-systems/<int:pk>/', views.TargetSystemDetailView.as_view(), name='target_system_detail'),
    path('target-systems/<int:pk>/edit/', views.TargetSystemUpdateView.as_view(), name='target_system_edit'),
    path('target-systems/<int:pk>/delete/', views.TargetSystemDeleteView.as_view(), name='target_system_delete'),
    path('target-systems/<int:pk>/history/', views.TargetSystemHistoryView.as_view(), name='target_system_history'),
    path('target-systems/<int:pk>/history/<int:version_pk>/', views.TargetSystemVersionDetailView.as_view(), name='target_system_version_detail'),
    
    # Backup Configurations CRUD
    path('backup-configuration/', views.BackupConfigurationListView.as_view(), name='backup_configuration_list'),
    path('backup-configuration/create/', views.BackupConfigurationCreateView.as_view(), name='backup_configuration_create'),
    path('backup-configuration/<int:pk>/', views.BackupConfigurationDetailView.as_view(), name='backup_configuration_detail'),
    path('backup-configuration/<int:pk>/edit/', views.BackupConfigurationUpdateView.as_view(), name='backup_configuration_edit'),
    path('backup-configuration/<int:pk>/delete/', views.BackupConfigurationDeleteView.as_view(), name='backup_configuration_delete'),
    path('backup-configuration/<int:pk>/history/', views.BackupConfigurationHistoryView.as_view(), name='backup_configuration_history'),
    path('backup-configuration/<int:pk>/history/<int:version_pk>/', views.BackupConfigurationVersionDetailView.as_view(), name='backup_configuration_version_detail'),
    
    path('system-types/', views.SystemTypeListView.as_view(), name='system_type_list'),
    path('system-types/create/', views.SystemTypeCreateView.as_view(), name='system_type_create'),
    path('system-types/<int:pk>/edit/', views.SystemTypeUpdateView.as_view(), name='system_type_edit'),
    path('system-types/<int:pk>/delete/', views.SystemTypeDeleteView.as_view(), name='system_type_delete'),

    # Environments
    path('environments/', views.EnvironmentListView.as_view(), name='environment_list'),
    path('environments/create/', views.EnvironmentCreateView.as_view(), name='environment_create'),
    path('environments/<int:pk>/edit/', views.EnvironmentUpdateView.as_view(), name='environment_edit'),
    path('environments/<int:pk>/delete/', views.EnvironmentDeleteView.as_view(), name='environment_delete'),

    # Backup Tools
    path('backup-tools/', views.BackupToolListView.as_view(), name='backup_tool_list'),
    path('backup-tools/create/', views.BackupToolCreateView.as_view(), name='backup_tool_create'),
    path('backup-tools/<int:pk>/edit/', views.BackupToolUpdateView.as_view(), name='backup_tool_edit'),
    path('backup-tools/<int:pk>/delete/', views.BackupToolDeleteView.as_view(), name='backup_tool_delete'),

    # REST API (ViewSet)
    # path('api/v1/', include(router.urls)),
    
    # Authentication
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html'
    ), name='login'),
    path('logout/', logout_view, name='logout'),
]