from django.urls import path
from . import views

urlpatterns = [
    path('home/', views.creator_view, name='creator_home'),
    path('comments/', views.youtube_comments_call, name='comments'),
    path('comments/save/', views.save_comments, name='save_comments'),
    path('comments/analyze/', views.analyze_comments, name='analyze_comments'),
    path('comments/story/', views.story_view, name='story_view'),
    path('comments/delete/', views.delete_all_articlecom, name='delete_all_articlecom'),
    path('data/', views.render_article_data, name='data_view'),
]
