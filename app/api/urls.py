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
    # Твой основной API
    path('', include(router.urls)),
    
    # НОВЫЕ: Эндпоинты для UI (AJAX polling)
    path('ui-refresh/dashboard/', views.api_ui_refresh_dashboard, name='api_ui_refresh_dashboard'),
    path('ui-refresh/operations/', views.api_ui_refresh_operations, name='api_ui_refresh_operations'),
    
    # НОВОЕ: Демо-страница для руководителя
    path('demo/', views.demo_dashboard, name='api_demo_dashboard'),
]