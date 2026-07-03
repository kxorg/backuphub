"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from core import views

# Swagger configuration
schema_view = get_schema_view(
    openapi.Info(
        title="BackupHub API",
        default_version='v1',
        description="REST API for centralized backup monitoring",
        contact=openapi.Contact(email="support@backuphub.local"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name="index"),
    path('api/', views.api, name="api"),
    
    # TargetSystems CRUD 
    path('target-systems/', views.system_settings, name="target_system_list"),
    path('target-systems/create/', views.system_create, name="target_system_create"),
    path('target-systems/<int:pk>/edit/', views.system_edit, name="target_system_edit"),
    path('target-systems/<int:pk>/delete/', views.system_delete, name="target_system_delete"),
    
    # Hosts CRUD 
    path('hosts/', views.servers, name="host_list"),
    path('hosts/create/', views.host_create, name="host_create"),
    path('hosts/<int:pk>/edit/', views.host_edit, name="host_edit"),
    path('hosts/<int:pk>/delete/', views.host_delete, name="host_delete"),
    
    # Backups 
    path('backups/', views.backups_list, name="backup_list"),
    path('backups/<uuid:pk>/', views.backup_detail, name="backup_detail"),
    
    # REST API
    path('api/v1/', include('core.urls')),
    
    # Swagger documentation
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/schema/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
]
