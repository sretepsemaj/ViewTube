from django.shortcuts import render, redirect
from django.conf import settings
from .models import ArticleVid
from django.db.models import Q
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os


# This function should render the `creator_home.html` template
def viewer_view(request):
    return render(request, 'viewer/viewhome.html')  # Ensure this template path exists

YOUTUBE_API_KEY = os.getenv('TUBE_API_KEY')

def youtube_video_call(request):
    """
    Fetch videos from YouTube using the YouTube Data API based on a keyword search.
    """
    videos = []
    error_message = None

    if request.method == 'POST':
        query = request.POST.get('query')  # Get the search keyword from the form
        print(f"Received search query: {query}")  # Debug: Log the received query

        if query:
            try:
                youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
                print("YouTube API client built successfully.")  # Debug: Confirm API client creation

                # Make the API call to search for videos based on the keyword
                api_request = youtube.search().list(
                    part='snippet',
                    q=query,
                    maxResults=10,  # Number of videos to retrieve
                    type='video',  # Ensure only videos are returned
                    order='relevance'  # Order by relevance to the query
                )
                print("API request prepared:", api_request)  # Debug: Log the API request details

                response = api_request.execute()
                print("API Response:", response)  # Debug: Log the entire API response

                for item in response.get('items', []):
                    video = {
                        'video_id': item['id']['videoId'],
                        'title': item['snippet']['title'],
                        'description': item['snippet']['description'],
                        'channel_title': item['snippet']['channelTitle'],
                        'published_at': item['snippet']['publishedAt'],
                        'thumbnail_url': item['snippet']['thumbnails']['high']['url']
                    }
                    print(f"Processed video: {video['title']} (ID: {video['video_id']})")  # Debug: Log each video processed
                    videos.append(video)

                if not videos:
                    error_message = "No videos found for the given keyword."
                    print(error_message)  # Debug: Log if no videos are found

                # Save videos to session for further processing if needed
                request.session['videos'] = videos
                print(f"Saved {len(videos)} videos to session.")  # Debug: Log the number of videos saved

            except HttpError as e:
                error_message = f"An HTTP error occurred: {e.resp.status} - {e.content}"
                print(error_message)  # Log the HTTP error
            except Exception as e:
                error_message = f"An error occurred: {str(e)}"
                print(error_message)  # Log any other errors
        else:
            error_message = "Please enter a keyword to search."
            print(error_message)  # Log if the query is empty

    context = {
        'videos': videos,
        'error_message': error_message,
        'query': request.POST.get('query', '')  # Preserve the search query in the form
    }
    return render(request, 'viewer/videos.html', context)

def save_video(request):
    if request.method == 'POST' and request.session.get('videos'):
        videos_data = request.session['videos']
        saved_count = 0
        error_messages = []

        for video in videos_data:
            try:
                if not ArticleVid.objects.filter(video_id=video['video_id']).exists():
                    ArticleVid.objects.create(
                        video_id=video['video_id'],
                        title=video['title'],
                        description=video['description'],
                        channel_title=video['channel_title'],
                        published_at=video['published_at'],
                        thumbnail_url=video['thumbnail_url']
                    )
                    saved_count += 1
                else:
                    print(f"Video {video['video_id']} already exists. Skipping.")
            except Exception as e:
                error_messages.append(f"Error saving video {video['video_id']}: {e}")
                print(f"Error saving video {video['video_id']}: {e}")

        # Clear videos from session after saving
        del request.session['videos']

        context = {
            'saved_count': saved_count,
            'error_messages': error_messages
        }
        return render(request, 'viewer/save_videos.html', context)
    
    # For GET requests or missing session data, redirect to home
    return redirect('video_data') 

def render_article_data(request):
    """
    Render all videos from the ArticleVid model to the data.html template.
    """
    filter_param = request.GET.get('filter', '')
    videos = ArticleVid.objects.all()

    if filter_param:
        videos = videos.filter(
            Q(title__icontains=filter_param) | 
            Q(description__icontains=filter_param) | 
            Q(channel_title__icontains=filter_param)
        )

    # Debugging output
    print(f"Number of videos passed to template: {videos.count()}")

    return render(request, 'viewer/data.html', {'videos': videos})
