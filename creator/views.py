from django.shortcuts import render, redirect
from django.http import JsonResponse
from googleapiclient.discovery import build
import os
from .models import ArticleCom
import math
import logging
import groq
from django.conf import settings

logger = logging.getLogger(__name__)

def creator_view(request):
    return render(request, 'creator/creathome.html')  # Use the app-specific path

# Replace 'YOUR_API_KEY' with your actual YouTube Data API key or load from environment variables
YOUTUBE_API_KEY = os.getenv('TUBE_API_KEY')
client = groq.Client(api_key=settings.GROQ_API_KEY)

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


def story_from_articlecoms():
    # Fetch all comments from the ArticleCom model with a token count of 300 or more
    try:
        article_coms = ArticleCom.objects.filter(token_count__gte=300)

        if not article_coms.exists():
            logger.warning("No comments found in ArticleCom with a sufficient token size.")
            return None, "No comments available to generate a story."

        generated_stories = []

        for comment in article_coms:
            logger.info(f"Processing Comment ID: {comment.comment_id} by {comment.author} with {comment.token_count} tokens.")

            # Prepare the message payload with the comment's text display
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a skilled writer for a major news station. Rewrite the following comment into a concise news story:"
                    ),
                },
                {
                    "role": "user",
                    "content": comment.text_display,  # Use the text of the comment
                },
            ]

            logger.info(f"Sending message content for comment ID: {comment.comment_id}")

            # Make the API call
            try:
                completion = client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1024,  # Limit output tokens
                    top_p=1,
                    stream=False,  # Set to False for a single response
                    stop=None,
                )

                # Extract the generated story from the response
                generated_story = completion.choices[0].message.content.strip()

                if not generated_story:
                    generated_story = "No story could be generated from this comment."

                logger.info(f"Story generated successfully for Comment ID: {comment.comment_id}.")

                # Append the generated story and comment details, including channel URL
                generated_stories.append({
                    'generated_story': generated_story,
                    'author': comment.author,
                    'published_at': comment.published_at,
                    'comment_id': comment.comment_id,
                    'channel_url': comment.channel_url  # Include the channel URL
                })

            except Exception as e:
                logger.error(f"Error generating story for Comment ID {comment.comment_id}: {str(e)}")
                continue

        if not generated_stories:
            return None, "No stories were generated from the comments."

        # Return all generated stories
        return generated_stories, None

    except Exception as e:
        logger.error(f"Error generating stories: {str(e)}")
        return None, f"Error: {str(e)}"

def story_view(request):
    # Fetch the generated stories and additional comment details
    stories_data, error_message = story_from_articlecoms()

    # Prepare the context for rendering the template
    context = {
        "stories": stories_data if stories_data else [],
        "error_message": error_message if not stories_data else None,
    }

    # Render the `story.html` template with the generated stories and comment details
    return render(request, "creator/story.html", context)