from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout
from django.shortcuts import redirect
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from api.views import api_ui_refresh_dashboard, api_ui_refresh_operations, api_ui_refresh_operation_detail,api_ui_refresh_target_system
from app.views import index


def logout_view(request):
    logout(request)
    return redirect('login')


urlpatterns = [
    # Dictionaries
    path('', include('dictionaries.urls')),
    # Systems
    path('', include('systems.urls')),
    # Configurations
    path('', include('configurations.urls')),
    # Operations
    path('', include('operations.urls')),
    # Search
    path('search/', include('search.urls')),

    # Dashboard
    path('', index, name='index'),

    # External API (v1)
    path('api/', include('api.urls')),

    # Auth
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html'
    ), name='login'),
    path('logout/', logout_view, name='logout'),

    # Admin
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/ui/refresh-dashboard/', api_ui_refresh_dashboard, name='api_ui_refresh_dashboard'),
    path('api/ui/refresh-operations/', api_ui_refresh_operations, name='api_ui_refresh_operations'),
    path('api/ui/refresh-operation/<int:pk>/', api_ui_refresh_operation_detail, name='api_ui_refresh_operation_detail'),
    path('api/ui/refresh-target-system/<int:pk>/', api_ui_refresh_target_system, name='api_ui_refresh_target_system'), 

]
