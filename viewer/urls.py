from django.urls import path
from . import views

urlpatterns = [
    path('', views.viewer_view, name='viewer_home'),
    path('video/', views.youtube_video_call, name='video'),
    path('save-video/', views.save_video, name='video_data'),
    path('vdata/', views.render_article_data, name='render_article_data'),
]
