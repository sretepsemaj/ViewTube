from django.shortcuts import render, redirect
from django.http import JsonResponse
from googleapiclient.discovery import build
import os
from .models import ArticleCom
import math

def creator_view(request):
    return render(request, 'creator/creathome.html')  # Use the app-specific path

# Replace 'YOUR_API_KEY' with your actual YouTube Data API key or load from environment variables
YOUTUBE_API_KEY = os.getenv('TUBE_API_KEY')

def youtube_comments_call(request):
    comments = []
    if request.method == 'POST':
        video_id = request.POST.get('video_id')

        if video_id:
            youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

            # Initial API request to get the first page of comments
            api_request = youtube.commentThreads().list(
                part='snippet',
                videoId=video_id,
                maxResults=100  # Set to 100 as this is the maximum per API call
            )
            response = api_request.execute()

            # Append the first page of comments
            while response:
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

                # Check if there is a next page of comments
                if 'nextPageToken' in response:
                    api_request = youtube.commentThreads().list(
                        part='snippet',
                        videoId=video_id,
                        maxResults=100,  # Maximum number of results per page
                        pageToken=response['nextPageToken']
                    )
                    response = api_request.execute()
                else:
                    break

            # Save comments to session for further processing
            request.session['comments'] = comments

    return render(request, 'creator/comments.html', {'comments': comments})

#def save_comments(request):
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

#def data_view(request):
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

#def render_article_data(request):
    """
    Render all articles from the ArticleCom model to the data.html template.
    """
    articles = ArticleCom.objects.all()  # Query all article comments
    # Debug output to verify the number of articles
    print(f"Number of articles passed to template: {articles.count()}")

    return render(request, 'creator/data.html', {'data': articles})


def estimate_tokens(text):
    """
    Estimate the number of tokens in the given text.
    """
    word_count = len(text.split())
    return math.ceil(word_count * 1.33)  # Rough estimation: 1.33 tokens per word

def save_comments(request):
    if request.method == 'POST' and request.session.get('comments'):
        comments_data = request.session['comments']
        saved_count = 0

        for comment in comments_data:
            # Estimate token size for each comment's text
            token_count = estimate_tokens(comment['text_display'])

            print(f"Attempting to save comment: {comment['comment_id']} by {comment['author']}, Tokens: {token_count}")
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
                        replies_count=comment.get('replies_count', 0),
                        token_count=token_count  # Assuming you add a `token_count` field to the model
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

def render_article_data(request):
    """
    Render all articles from the ArticleCom model to the data.html template.
    """
    articles = ArticleCom.objects.all().order_by('-token_count')  # Sort by token count descending
    print(f"Number of articles passed to template: {articles.count()}")
    return render(request, 'creator/data.html', {'data': articles})

def data_view(request):
    filter_param = request.GET.get('filter', '')
    data_query = ArticleCom.objects.all().order_by('-token_count')  # Sort by token count descending

    if filter_param:
        data_query = data_query.filter(
            Q(author__icontains=filter_param) | 
            Q(text_display__icontains=filter_param) | 
            Q(channel_url__icontains=filter_param)
        )

    # Debugging output
    print(f"Data passed to template: {data_query}")
    return render(request, 'creator/data.html', {'data': data_query})