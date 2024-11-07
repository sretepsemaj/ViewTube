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

def save_comments(request):
    if request.method == 'POST' and request.session.get('comments'):
        comments_data = request.session['comments']
        saved_count = 0

        for comment in comments_data:
            print(f"Attempting to save comment: {comment['comment_id']} by {comment['author']}")
            try:
                if not ArticleCom.objects.filter(comment_id=comment['comment_id']).exists():
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
                    saved_count += 1
                    print(f"Comment {comment['comment_id']} saved successfully.")
                else:
                    print(f"Comment {comment['comment_id']} already exists. Skipping.")
            except Exception as e:
                print(f"Error saving comment {comment['comment_id']}: {e}")

        print(f"Total comments saved: {saved_count}")
        return redirect('article_data')  # Replace with the correct name of your data view

    return render(request, 'creator/save_comments.html')

def data_view(request):
    filter_param = request.GET.get('filter', '')
    data_query = ArticleCom.objects.all()

    if filter_param:
        data_query = data_query.filter(
            Q(author__icontains=filter_param) | 
            Q(text_display__icontains=filter_param) | 
            Q(channel_url__icontains=filter_param)
        )

    # Debugging output
    print(f"Data passed to template: {data_query}")

    return render(request, 'creator/data.html', {'data': data_query})

def render_article_data(request):
    """
    Render all articles from the ArticleCom model to the data.html template.
    """
    articles = ArticleCom.objects.all()  # Query all article comments
    # Debug output to verify the number of articles
    print(f"Number of articles passed to template: {articles.count()}")

    return render(request, 'creator/data.html', {'data': articles})