from django.urls import path
from . import views

urlpatterns = [
    path('system-types/', views.SystemTypeListView.as_view(), name='system_type_list'),
    path('system-types/create/', views.SystemTypeCreateView.as_view(), name='system_type_create'),
    path('system-types/<int:pk>/edit/', views.SystemTypeUpdateView.as_view(), name='system_type_edit'),
    path('system-types/<int:pk>/delete/', views.SystemTypeDeleteView.as_view(), name='system_type_delete'),
    
    path('environments/', views.EnvironmentListView.as_view(), name='environment_list'),
    path('environments/create/', views.EnvironmentCreateView.as_view(), name='environment_create'),
    path('environments/<int:pk>/edit/', views.EnvironmentUpdateView.as_view(), name='environment_edit'),
    path('environments/<int:pk>/delete/', views.EnvironmentDeleteView.as_view(), name='environment_delete'),
    
    path('backup-tools/', views.BackupToolListView.as_view(), name='backup_tool_list'),
    path('backup-tools/create/', views.BackupToolCreateView.as_view(), name='backup_tool_create'),
    path('backup-tools/<int:pk>/edit/', views.BackupToolUpdateView.as_view(), name='backup_tool_edit'),
    path('backup-tools/<int:pk>/delete/', views.BackupToolDeleteView.as_view(), name='backup_tool_delete'),

    path('information-systems/', views.InformationSystemListView.as_view(), name='information_system_list'),
    path('information-systems/create/', views.InformationSystemCreateView.as_view(), name='information_system_create'),
    path('information-systems/<int:pk>/edit/', views.InformationSystemUpdateView.as_view(), name='information_system_edit'),
    path('information-systems/<int:pk>/delete/', views.InformationSystemDeleteView.as_view(), name='information_system_delete'),

]