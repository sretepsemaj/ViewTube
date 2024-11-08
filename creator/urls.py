from django.urls import path
from . import views

urlpatterns = [
    path('', views.creator_view, name='creator_home'),  # Name your path to use in templates
    path('comments/', views.youtube_comments_call, name='comments'),
    path('save-comments/', views.save_comments, name='save_comments'),
    path('data/', views.render_article_data, name='article_data'),
]


