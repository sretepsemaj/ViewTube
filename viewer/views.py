from django.shortcuts import render
import os
from googleapiclient.discovery import build  # Add this import

# This function should render the `creator_home.html` template
def viewer_view(request):
    return render(request, 'viewer/viewhome.html')  # Ensure this template path exists

YOUTUBE_API_KEY = os.getenv('TUBE_API_KEY')

def youtube_api_call(request):
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

    # Example API call
    api_request = youtube.search().list(
        part='snippet',
        q='technology',
        type='video',
        maxResults=5
    )
    response = api_request.execute()

    # Pass the response data to the template
    return render(request, 'viewer/tubeapi.html', {'response': response})