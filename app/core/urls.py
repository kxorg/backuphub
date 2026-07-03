from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout
from django.shortcuts import redirect
from rest_framework.routers import DefaultRouter
from . import views

# Logout handler via GET request
def logout_view(request):
    logout(request)
    return redirect('login')

router = DefaultRouter()
router.register(r'target-system', views.TargetSystemViewSet, basename='target-system')
router.register(r'host', views.HostViewSet, basename='host')
router.register(r'backup', views.BackupViewSet, basename='backup')

urlpatterns = [
    path('backup/create/', views.BackupCreateView.as_view(), name='backup_api_create'),
    path('backup/<uuid:backup_id>/update/', views.BackupUpdateView.as_view(), name='backup_api_update'),
    path('', include(router.urls)),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', logout_view, name='logout'),
]