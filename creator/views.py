from django.shortcuts import render, redirect
from django.http import JsonResponse
from googleapiclient.discovery import build
import os
from .models import ArticleCom
import math
import logging
import groq
from django.conf import settings
from django.contrib import messages
from django.db.models import Avg
from googleapiclient.errors import HttpError


logger = logging.getLogger(__name__)

def creator_view(request):
    return render(request, 'creator/creathome.html')  # Use the app-specific path

# Replace 'YOUR_API_KEY' with your actual YouTube Data API key or load from environment variables
YOUTUBE_API_KEY = os.getenv('TUBE_API_KEY')
client = groq.Client(api_key=settings.GROQ_API_KEY)

def estimate_tokens(text):
    word_count = len(text.split())
    return math.ceil(word_count * 1.33)

# Fetch and display comments
def youtube_comments_call(request):
    comments = []
    if request.method == 'POST' and 'fetch_comments' in request.POST:
        video_id = request.POST.get('video_id')
        if video_id:
            youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
            try:
                api_request = youtube.commentThreads().list(
                    part='snippet',
                    videoId=video_id,
                    maxResults=100
                )
                response = api_request.execute()

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

                    if 'nextPageToken' in response:
                        api_request = youtube.commentThreads().list(
                            part='snippet',
                            videoId=video_id,
                            maxResults=100,
                            pageToken=response['nextPageToken']
                        )
                        response = api_request.execute()
                    else:
                        break

                request.session['comments'] = comments
                messages.success(request, f"{len(comments)} comments fetched successfully.")
            except HttpError as e:
                messages.error(request, f"An HTTP error occurred: {e.resp.status} - {e.content}")
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")

    return render(request, 'creator/comments.html', {'comments': comments})

# Save fetched comments to the database
def save_comments(request):
    if request.method == 'POST' and request.session.get('comments'):
        comments_data = request.session['comments']
        saved_count = 0

        for comment in comments_data:
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
                        token_count=estimate_tokens(comment['text_display'])
                    )
                    saved_count += 1
            except Exception as e:
                messages.error(request, f"Error saving comment {comment['comment_id']}: {e}")

        if saved_count > 0:
            messages.success(request, f"{saved_count} comments saved successfully.")
        else:
            messages.info(request, "No new comments were saved.")

        # Redirect to a page showing saved data or the comments page
        return redirect('article_data')  # Replace 'data_view' with the name of your view that shows saved data

    messages.error(request, "No comments to save or invalid request.")
    return redirect('comments')  # Redirect back if no comments are found or if not a POST request

# Delete all entries in ArticleCom
def delete_all_articlecom(request):
    if request.method == 'POST':
        ArticleCom.objects.all().delete()
        messages.success(request, "All records in ArticleCom have been successfully deleted.")
        return redirect('comments')

# Render all articles sorted by token count
def render_article_data(request):
    articles = ArticleCom.objects.all().order_by('-token_count')
    average_tokens = articles.aggregate(Avg('token_count'))['token_count__avg']
    messages.info(request, f"Average token size: {average_tokens:.2f}" if average_tokens else "No data to calculate average.")
    return render(request, 'creator/data.html', {'data': articles})



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