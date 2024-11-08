from django.urls import path
from . import views

urlpatterns = [
    path('', views.viewer_view, name='viewer_view'),  # Name your path to use in templates
    path('video/', views.youtube_video_call, name='video'),
    path('save-video/', views.save_video, name='save_video'),
    path('vdata/', views.render_article_data, name='video_data'),
]
