from django.urls import path
from . import views  # This imports views from the same folder

urlpatterns = [
    path('', views.home, name='creator_home'),  # Correct reference to views.home
]