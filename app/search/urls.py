from django.urls import path
from . import views

urlpatterns = [
    path('', views.SearchPageView.as_view(), name='search_page'),
]