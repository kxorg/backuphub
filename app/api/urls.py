from django.urls import path, include
from api.views import api_global_search

urlpatterns = [
    path('v1/', include('api.v1.urls')),
    path('search/', api_global_search, name = 'api_global_search')
]