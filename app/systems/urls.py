from django.urls import path
from . import views

urlpatterns = [
    path('target-systems/', views.TargetSystemListView.as_view(), name='target_system_list'),
    path('target-systems/create/', views.TargetSystemCreateView.as_view(), name='target_system_create'),
    path('target-systems/<int:pk>/', views.TargetSystemDetailView.as_view(), name='target_system_detail'),
    path('target-systems/<int:pk>/edit/', views.TargetSystemUpdateView.as_view(), name='target_system_edit'),
    path('target-systems/<int:pk>/delete/', views.TargetSystemDeleteView.as_view(), name='target_system_delete'),
    path('target-systems/<int:pk>/history/', views.TargetSystemHistoryView.as_view(), name='target_system_history'),
    path('target-systems/<int:pk>/history/<int:version_pk>/', views.TargetSystemVersionDetailView.as_view(), name='target_system_version_detail'),
]