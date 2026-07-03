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
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('', views.index, name="index"),
    path('api/', views.api, name="api"),
    
    # Journal backup
    path('journal_backup/', views.journal_backup, name="journal_backup"),
    path('backups/<uuid:pk>/', views.backup_detail, name="backup_detail_web"),
    
    # System settings (CRUD)
    path('system_settings/', views.system_settings, name="system_settings"),
    path('system_settings/create/', views.system_create, name="system_create"),
    path('system_settings/<int:pk>/edit/', views.system_edit, name="system_edit"),
    path('system_settings/<int:pk>/delete/', views.system_delete, name="system_delete"),
    
    # Servers (CRUD)
    path('servers/', views.servers, name="servers"),
    path('servers/create/', views.host_create, name="host_create"),
    path('servers/<int:pk>/edit/', views.host_edit, name="host_edit"),
    path('servers/<int:pk>/delete/', views.host_delete, name="host_delete"),
    
    # API 
    path('api/v1/', include('core.urls')),
]
