from django.db import models


class Transcription(models.Model):
    title = models.CharField(max_length=200, blank=True)
    text = models.TextField()
    language = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or self.text[:50]