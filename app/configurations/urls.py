from django.urls import path
from . import views

urlpatterns = [
    path('backup-configuration/', views.BackupConfigurationListView.as_view(), name='backup_configuration_list'),
    path('backup-configuration/create/', views.BackupConfigurationCreateView.as_view(), name='backup_configuration_create'),
    path('backup-configuration/<int:pk>/', views.BackupConfigurationDetailView.as_view(), name='backup_configuration_detail'),
    path('backup-configuration/<int:pk>/edit/', views.BackupConfigurationUpdateView.as_view(), name='backup_configuration_edit'),
    path('backup-configuration/<int:pk>/delete/', views.BackupConfigurationDeleteView.as_view(), name='backup_configuration_delete'),
    path('backup-configuration/<int:pk>/history/', views.BackupConfigurationHistoryView.as_view(), name='backup_configuration_history'),
    path('backup-configuration/<int:pk>/history/<int:version_pk>/', views.BackupConfigurationVersionDetailView.as_view(), name='backup_configuration_version_detail'),
]