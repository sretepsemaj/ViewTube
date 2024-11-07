from django.urls import path
from . import views

urlpatterns = [
    path('', views.creator_view, name='creator_home'),  # Name your path to use in templates
    path('tubeapi/', views.youtube_api_call, name='tubeapi'),
    path('comments/', views.youtube_comments_call, name='comments'),
    path('populate/', views.populate_comments, name='populate_comments'),
    path('data/', views.render_article_data, name='article_data'),
]


