from django.db import models

class ArticleCom(models.Model):
    comment_id = models.CharField(max_length=255, unique=True)
    author = models.CharField(max_length=255)
    profile_image = models.URLField(max_length=500)
    channel_url = models.URLField(max_length=500)
    text_display = models.TextField()
    published_at = models.DateTimeField()
    like_count = models.IntegerField()
    viewer_rating = models.CharField(max_length=50, blank=True, null=True)
    can_rate = models.BooleanField()
    replies_count = models.IntegerField()
    token_count = models.IntegerField(null=True, blank=True)
    sentiment_score = models.FloatField(default=0.0)  # New field for sentiment analysis

    def __str__(self):
        return f"{self.author} - {self.comment_id}"