import os
import math
import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Avg
from .models import ArticleCom
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from textblob import TextBlob
import groq  # Ensure Groq SDK is installed and imported
from django.conf import settings

# Initialize the logger
logger = logging.getLogger(__name__)

# Replace 'YOUR_API_KEY' with your actual YouTube Data API key or load from environment variables
YOUTUBE_API_KEY = os.getenv('TUBE_API_KEY')

# Initialize the Groq client using the API key from settings
client = groq.Client(api_key=settings.GROQ_API_KEY)

# Function to estimate token count
def estimate_tokens(text):
    word_count = len(text.split())
    return math.ceil(word_count * 1.33)

# Function to perform sentiment analysis
def analyze_sentiment(text):
    analysis = TextBlob(text)
    return analysis.sentiment.polarity  # Returns a value between -1 (negative) and 1 (positive)

# Function to prepare comment batches based on token count
def prepare_comment_batches():
    comments = ArticleCom.objects.all().order_by('-token_count')
    average_tokens = ArticleCom.objects.aggregate(Avg('token_count'))['token_count__avg'] or 300
    batch_size = int(average_tokens)  # Customize as needed

    batches = []
    current_batch = []
    current_tokens = 0

    for comment in comments:
        if current_tokens + comment.token_count > batch_size:
            if current_batch:
                batches.append(current_batch)
                current_batch = []
                current_tokens = 0
        current_batch.append(comment)
        current_tokens += comment.token_count

    if current_batch:
        batches.append(current_batch)

    return batches

# Function to generate articles from comments
def generate_articles_from_comments():
    try:
        # Group comments by token size into batches
        comment_batches = prepare_comment_batches()

        generated_articles = []

        for batch in comment_batches:
            # Combine comments in the batch into a single string
            batch_text = "\n###\n".join(comment.text_display for comment in batch)
            
            # Prepare Groq message payload
            messages = [
                {"role": "system", "content": "You are a journalist summarizing user feedback into an article."},
                {"role": "user", "content": batch_text}
            ]

            # Send to Groq for processing
            try:
                completion = client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1024,
                    top_p=1
                )

                # Extract and format the generated article
                generated_article = completion.choices[0].message.content.strip()
                generated_articles.append(generated_article)

                logger.info(f"Generated article: {generated_article[:100]}...")  # Debug: print the first 100 characters

            except Exception as e:
                logger.error(f"Error processing batch: {e}")
                continue

        return generated_articles

    except Exception as e:
        logger.error(f"Error in article generation: {e}")
        return None

# Function to generate stories from high-token comments
def story_from_articlecoms():
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

        return generated_stories, None

    except Exception as e:
        logger.error(f"Error generating stories: {str(e)}")
        return None, f"Error: {str(e)}"

# View to render the home page
def creator_view(request):
    return render(request, 'creator/creathome.html')  # Use the app-specific path

# View to fetch comments
def youtube_comments_call(request):
    comments = []
    if request.method == 'POST' and 'fetch_comments' in request.POST:
        video_id = request.POST.get('video_id')

        if video_id:
            youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

            # Initial API request to get the first page of comments
            try:
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
                            maxResults=100,
                            pageToken=response['nextPageToken']
                        )
                        response = api_request.execute()
                    else:
                        break

                # Save comments to session for further processing
                request.session['comments'] = comments
                messages.success(request, f"{len(comments)} comments fetched successfully.")
            except HttpError as e:
                messages.error(request, f"An HTTP error occurred: {e.resp.status} - {e.content}")
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")

    return render(request, 'creator/comments.html', {'comments': comments})

# View to save comments
def save_comments(request):
    if request.method == 'POST' and request.session.get('comments'):
        comments_data = request.session['comments']
        saved_count = 0
        for comment in comments_data:
            token_count = estimate_tokens(comment['text_display'])  # Calculate token_count once here
            sentiment_score = analyze_sentiment(comment['text_display'])  # Perform sentiment analysis
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
                        token_count=token_count,  # Save the calculated token_count
                        sentiment_score=sentiment_score  # Save the sentiment score
                    )
                    saved_count += 1
            except Exception as e:
                messages.error(request, f"Error saving comment {comment['comment_id']}: {e}")

        if saved_count > 0:
            messages.success(request, f"{saved_count} comments saved successfully.")
        else:
            messages.info(request, "No new comments were saved.")

        # Redirect to data view after saving
        return redirect('data_view')  # Ensure this matches your URL name

    messages.error(request, "No comments to save or invalid request.")
    return redirect('save_comments')  # Redirect back if no comments are found or if not a POST request

# View to delete all comments
def delete_all_articlecom(request):
    if request.method == 'POST':
        ArticleCom.objects.all().delete()
        messages.success(request, "All records in ArticleCom have been successfully deleted.")
        return redirect('comments')  # Ensure this matches your URL name

    return render(request, 'creator/comments.html')

# View to analyze comments and generate articles
def analyze_comments(request):
    if request.method == 'POST' and 'analyze_comments' in request.POST:
        generated_articles = generate_articles_from_comments()

        if generated_articles:
            messages.success(request, "Comments analyzed successfully.")
            return render(request, 'creator/analysis.html', {'generated_articles': generated_articles})
        else:
            messages.error(request, "No articles were generated. Please try again.")
            return redirect('comments')

    messages.error(request, "Invalid request.")
    return redirect('comments')

# View to generate and render stories from high-token comments
def story_from_articlecoms():
    # Filter comments with 200 or more tokens
    article_coms = ArticleCom.objects.filter(token_count__gte=200)
    
    if not article_coms.exists():
        return [], "No comments found with a sufficient token size to generate stories."

    generated_stories = []

    for comment in article_coms:
        try:
            # Create the message payload for the Groq API
            messages = [
                {
                    "role": "system",
                    "content": "take the comments and make a list of all the points the viewer makes in the comment section:"
                },
                {
                    "role": "user",
                    "content": comment.text_display
                }
            ]

            # Send to Groq or equivalent for processing
            completion = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
                top_p=1
            )

            # Extract the generated story from the response
            generated_story = completion.choices[0].message.content.strip()

            # Append the generated story and relevant comment information
            generated_stories.append({
                'generated_story': generated_story,
                'author': comment.author,
                'published_at': comment.published_at.strftime('%Y-%m-%d %H:%M'),
                'comment_id': comment.comment_id,
                'channel_url': comment.channel_url
            })

        except Exception as e:
            logger.error(f"Error generating story for Comment ID {comment.comment_id}: {str(e)}")
            continue  # Continue processing the next comments even if one fails

    if not generated_stories:
        return [], "Stories were generated, but all were empty."

    return generated_stories, None

# View to generate and render stories from comments with 200+ tokens
def story_view(request):
    if request.method == 'POST' and 'generate_stories' in request.POST:
        # Get generated stories and any error messages
        stories_data, error_message = story_from_articlecoms()

        if stories_data:
            messages.success(request, f"{len(stories_data)} stories generated successfully.")
        elif error_message:
            messages.error(request, error_message)

        context = {
            "stories": stories_data if stories_data else [],
            "error_message": error_message if not stories_data else None,
        }

        return render(request, "creator/story.html", context)

    messages.error(request, "Invalid request.")
    return redirect('comments')

# View to render data
def render_article_data(request):
    articles = ArticleCom.objects.all().order_by('-token_count')
    average_tokens = articles.aggregate(Avg('token_count'))['token_count__avg']
    if average_tokens:
        messages.info(request, f"Average token size: {average_tokens:.2f}")
    else:
        messages.info(request, "No data to calculate average.")
    return render(request, 'creator/data.html', {'data': articles})

def sentiment_analysis_view(request):
    # Retrieve sentiment scores from the database
    comments = ArticleCom.objects.all()
    positive_count = comments.filter(sentiment_score__gt=0.1).count()
    neutral_count = comments.filter(sentiment_score__lte=0.1, sentiment_score__gte=-0.1).count()
    negative_count = comments.filter(sentiment_score__lt=-0.1).count()

    total_comments = comments.count()
    if total_comments > 0:
        positive_percentage = (positive_count / total_comments) * 100
        neutral_percentage = (neutral_count / total_comments) * 100
        negative_percentage = (negative_count / total_comments) * 100
        average_sentiment = sum(comment.sentiment_score for comment in comments) / total_comments
    else:
        positive_percentage = neutral_percentage = negative_percentage = average_sentiment = 0

    context = {
        'positive_percentage': positive_percentage,
        'neutral_percentage': neutral_percentage,
        'negative_percentage': negative_percentage,
        'total_comments': total_comments,
        'average_sentiment': average_sentiment
    }
    return render(request, 'creator/analysis.html', context)
