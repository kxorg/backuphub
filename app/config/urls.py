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
    
    # Web interface
    path('', views.index, name="index"),
    path('api/', views.api, name="api"),
    
    # Magazine backup
    path('magazineHub/', views.magazineHub, name="magazineHub"),
    path('backups/<uuid:pk>/', views.backup_detail, name="backup_detail_web"),
    
    # System settings (CRUD)
    path('settings/', views.settings, name="settings"),
    path('settings/create/', views.system_create, name="system_create"),
    path('settings/<int:pk>/edit/', views.system_edit, name="system_edit"),
    path('settings/<int:pk>/delete/', views.system_delete, name="system_delete"),
    
    # Servers (CRUD)
    path('servers/', views.servers, name="servers"),
    path('servers/create/', views.host_create, name="host_create"),
    path('servers/<int:pk>/edit/', views.host_edit, name="host_edit"),
    path('servers/<int:pk>/delete/', views.host_delete, name="host_delete"),
    
    # REST API
    path('api/v1/', include('core.urls')),
    
    # Swagger documentation
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/schema/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
]
