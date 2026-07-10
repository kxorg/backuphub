from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(
    r'backup-operations',
    views.BackupOperationViewSet,
    basename='backup-operation'
)

urlpatterns = [
    path('', include(router.urls)),
    path('ui-refresh/dashboard/', views.api_ui_refresh_dashboard, name='api_ui_refresh_dashboard'),
    
]