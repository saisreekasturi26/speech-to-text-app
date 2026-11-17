from django.db import models


class Transcription(models.Model):
    LANGUAGE_LABELS = {"mix": "Hindi + English", "hi": "Hindi", "en": "English"}

    title = models.CharField(max_length=200, blank=True)
    text = models.TextField()
    language = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def language_label(self):
        return self.LANGUAGE_LABELS.get(self.language, self.language or "-")

    def __str__(self):
        return self.title or self.text[:50]