from django.shortcuts import render, redirect
from django.http import JsonResponse
from googleapiclient.discovery import build
import os
from .models import ArticleCom

def creator_view(request):
    return render(request, 'creator/creathome.html')  # Use the app-specific path

# Replace 'YOUR_API_KEY' with your actual YouTube Data API key or load from environment variables
YOUTUBE_API_KEY = os.getenv('TUBE_API_KEY')

def youtube_api_call(request):
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

    # Example API call: Search for videos related to "technology"
    api_request = youtube.search().list(
        part='snippet',
        q='technology',
        type='video',
        maxResults=5  # Adjust the number as needed
    )
    response = api_request.execute()

    # For testing, render the response in a simple HTML template
    return render(request, 'creator/tubeapi.html', {'response': response})

def youtube_comments_call(request):
    comments = []
    if request.method == 'POST':
        video_id = request.POST.get('video_id')

        if video_id:
            youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

            # Make the API call to retrieve comment threads
            api_request = youtube.commentThreads().list(
                part='snippet',
                videoId=video_id,
                maxResults=10  # Adjust the number of comments as needed
            )
            response = api_request.execute()

            for item in response.get('items', []):
                comment_data = item['snippet']['topLevelComment']['snippet']
                comment = {
                    'comment_id': item['id'],
                    'author': comment_data.get('authorDisplayName', ''),
                    'profile_image': comment_data.get('authorProfileImageUrl', ''),
                    'channel_url': comment_data.get('authorChannelUrl', ''),
                    'text_display': comment_data.get('textDisplay', ''),
                    'published_at': comment_data.get('publishedAt', ''),
                    'like_count': comment_data.get('likeCount', 0),
                    'viewer_rating': comment_data.get('viewerRating', 'none'),
                    'can_rate': comment_data.get('canRate', False),
                    'replies_count': item.get('snippet', {}).get('totalReplyCount', 0)
                }
                comments.append(comment)

            # Save comments to session for further processing
            request.session['comments'] = comments

    return render(request, 'creator/comments.html', {'comments': comments})

def populate_comments(request):
    if request.method == 'POST' and request.session.get('comments'):
        comments_data = request.session['comments']
        for comment in comments_data:
            try:
                # Log each comment being saved for debugging
                print(f"Saving comment: {comment['comment_id']} by {comment['author']}")
                ArticleCom.objects.create(
                    comment_id=comment['comment_id'],
                    author=comment['author'],
                    profile_image=comment['profile_image'],
                    channel_url=comment['channel_url'],
                    text_display=comment['text_display'],
                    published_at=comment['published_at'],
                    like_count=comment['like_count'],
                    viewer_rating=comment.get('viewer_rating', 'none'),
                    can_rate=comment['can_rate'],
                    replies_count=comment.get('replies_count', 0)
                )
            except Exception as e:
                print(f"Error saving comment {comment['comment_id']}: {e}")

        # Retrieve all saved comments to display on the page
        saved_comments = ArticleCom.objects.all()
        return render(request, 'creator/populate.html', {'saved_comments': saved_comments})

    return render(request, 'creator/populate.html', {'saved_comments': []})

def render_article_data(request):
    # Retrieve all ArticleCom entries from the database
    articles = ArticleCom.objects.all()

    # Render the data in the 'data.html' template
    return render(request, 'creator/data.html', {'articles': articles})