from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'systems', views.TargetSystemViewSet, basename='system')
router.register(r'hosts', views.HostViewSet, basename='host')
router.register(r'backups-list', views.BackupViewSet, basename='backup-list')

urlpatterns = [
    path('', include(router.urls)),
    
    path('backups/', views.BackupCreateView.as_view(), name='backup-create'),
    path('backups/<uuid:backup_id>/', views.BackupUpdateView.as_view(), name='backup-update'),
]