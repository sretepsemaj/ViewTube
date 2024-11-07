from django.shortcuts import render
from django.http import JsonResponse
from googleapiclient.discovery import build
import os

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
    comments = None
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
            comments = response['items']

    return render(request, 'creator/comments.html', {'comments': comments})
