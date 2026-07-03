from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout
from django.shortcuts import redirect
from rest_framework.routers import DefaultRouter
from . import views

# Обработчик выхода через GET-запрос
def logout_view(request):
    logout(request)
    return redirect('login')

router = DefaultRouter()
router.register(r'systems', views.TargetSystemViewSet, basename='system')
router.register(r'hosts', views.HostViewSet, basename='host')
router.register(r'backups-list', views.BackupViewSet, basename='backup-list')

urlpatterns = [
    path('', include(router.urls)),
    
    path('backups/', views.BackupCreateView.as_view(), name='backup-create'),
    path('backups/<uuid:backup_id>/', views.BackupUpdateView.as_view(), name='backup-update'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', logout_view, name='logout'),

    path('dashboard/', views.index, name='index'),
    path('servers/', views.servers, name='servers'),
    path('settings-ui/', views.settings, name='settings-page'),
    path('magazine/', views.magazineHub, name='magazine-hub'),
    path('api-ui/', views.api, name='api-ui'),
]