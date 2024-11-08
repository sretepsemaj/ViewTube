from django.urls import path
from . import views

urlpatterns = [
    path('', views.viewer_view, name='viewer_home'),  # Name your path to use in templates
]
