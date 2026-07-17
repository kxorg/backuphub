from django.urls import path
from . import views

urlpatterns = [
    path('backup-operations/', views.BackupOperationListView.as_view(), name='backup_operation_list'),
    path('backup-operations/<int:pk>/', views.BackupOperationDetailView.as_view(), name='backup_operation_detail'),
]