from django.shortcuts import render, redirect
from django.conf import settings
from .models import ArticleVid
from django.db.models import Q
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
from django.http import HttpResponse

# This function should render the `creator_home.html` template
def viewer_view(request):
    return render(request, 'viewer/viewhome.html')  # Ensure this template path exists

YOUTUBE_API_KEY = os.getenv('TUBE_API_KEY')

def youtube_video_call(request):
    """
    Fetch YouTube videos using a search query or a specific video ID and render to different templates.
    """
    videos = []
    error_message = None
    query = request.POST.get('query', '')
    video_id = request.POST.get('video_id', '').strip()
    search_type = request.POST.get('search_type', '')  # Capture the search type

    # Debugging output
    print(f"Method: {request.method}")
    print(f"Query: {query}")
    print(f"Video ID: {video_id}")
    print(f"Search Type: {search_type}")
    print(f"POST data: {request.POST}")

    if request.method == 'POST':
        try:
            youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

            if search_type == 'video_id_search' and video_id:
                print("Searching by video ID...")
                api_request = youtube.videos().list(
                    part='snippet,statistics',
                    id=video_id
                )
                print("Initiating video ID API request...")
                response = api_request.execute()
                print(f"API response for video ID: {response}")

                if response.get('items'):
                    video = response['items'][0]
                    videos.append({
                        'video_id': video['id'],
                        'title': video['snippet']['title'],
                        'description': video['snippet']['description'],
                        'channel_title': video['snippet']['channelTitle'],
                        'published_at': video['snippet']['publishedAt'],
                        'thumbnail_url': video['snippet']['thumbnails']['high']['url'],
                    })
                else:
                    error_message = "Video not found."
                    print("Video not found.")

            elif search_type == 'keyword_search' and query:
                print("Searching by keyword...")
                api_request = youtube.search().list(
                    part='snippet',
                    q=query,
                    maxResults=10,
                    type='video',
                    order='relevance'
                )
                response = api_request.execute()
                print(f"Response for keyword search: {response}")

                for item in response.get('items', []):
                    videos.append({
                        'video_id': item['id']['videoId'],
                        'title': item['snippet']['title'],
                        'description': item['snippet']['description'],
                        'channel_title': item['snippet']['channelTitle'],
                        'published_at': item['snippet']['publishedAt'],
                        'thumbnail_url': item['snippet']['thumbnails']['high']['url'],
                    })

                if not videos:
                    error_message = "No videos found for the given keyword."

        except HttpError as e:
            error_message = f"An HTTP error occurred: {e.resp.status} - {e.content}"
            print(error_message)
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            print(f"General exception: {e}")

    context = {
        'videos': videos,
        'error_message': error_message,
        'query': query,
        'video_id': video_id
    }

    # Render different templates based on search type
    if search_type == 'video_id_search':
        return render(request, 'viewer/idvideo.html', context)
    elif search_type == 'keyword_search':
        return render(request, 'viewer/keyword.html', context)
    else:
        # Fallback template if needed
        return render(request, 'viewer/videos.html', context)



def get_video_captions(video_id):
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        
        # Get the list of captions for the video
        captions_request = youtube.captions().list(
            part="id,snippet",  # Request the ID and snippet (language, name, etc.)
            videoId=video_id
        )
        
        captions_response = captions_request.execute()
        
        if 'items' in captions_response:
            caption = captions_response['items'][0]  # Get the first caption available
            caption_id = caption['id']
            caption_language = caption['snippet']['language']
            print(f"Captions available for video: {video_id}, language: {caption_language}")
            
            return caption_id  # Return caption ID for further processing
        else:
            print("No captions available for this video.")
            return None
    
    except HttpError as e:
        print(f"An error occurred: {e}")
        return None

def download_caption(caption_id):
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        
        # Download the caption in 'srt' format
        captions_request = youtube.captions().download(
            id=caption_id,
            tfmt="srt"  # You can also use 'ttml' for a different format
        )
        
        caption_content = captions_request.execute()
        print(f"Downloaded caption: {caption_content}")
        
        return caption_content  # You will receive the captions as text or file content
    
    except HttpError as e:
        print(f"An error occurred: {e}")
        return None

def download_caption_view(request, video_id):
    caption_id = get_video_captions(video_id)
    if caption_id:
        caption_content = download_caption(caption_id)
        if caption_content:
            # Serve the caption content as a downloadable response
            response = HttpResponse(caption_content, content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename="caption_{video_id}.srt"'
            return response
        else:
            return HttpResponse("Failed to download the caption.", status=500)
    else:
        return HttpResponse("No captions available for this video.", status=404)


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

from google.oauth2 import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import google.auth.transport.requests

# Specify the required scopes for the YouTube Data API.
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']

# Run the OAuth flow.
flow = InstalledAppFlow.from_client_secrets_file('path/to/credentials.json', SCOPES)
credentials = flow.run_local_server(port=0)

# Use the credentials in your requests.
youtube = build('youtube', 'v3', credentials=credentials)