from django.urls import path, include
from .views import api_ui_refresh_dashboard

urlpatterns = [
    path('v1/', include('api.v1.urls')),
    path('ui/refresh-dashboard/', api_ui_refresh_dashboard, name='api_ui_refresh_dashboard'),
]