from django.urls import path, include
from rest_framework.routers import DefaultRouter

from api.v1.backup_operations.views import BackupOperationViewSet


router = DefaultRouter()
router.register(
    r'backup-operations',
    BackupOperationViewSet,
    basename='backup-operation',
)

urlpatterns = [
    path('', include(router.urls)),
]