from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='viewer_home'),  # Ensure you have at least one valid path
]
