from django.db import models

class ArticleVid(models.Model):
    video_id = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    channel_title = models.CharField(max_length=255)
    published_at = models.DateTimeField()
    thumbnail_url = models.URLField()

    def __str__(self):
        return self.title
