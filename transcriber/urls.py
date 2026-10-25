from django.urls import path

from . import views

app_name = "transcriber"

urlpatterns = [
    path("", views.TranscriptionListView.as_view(), name="list"),
    path("new/", views.TranscriptionCreateView.as_view(), name="create"),
    path("<int:pk>/", views.TranscriptionDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.TranscriptionUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", views.TranscriptionDeleteView.as_view(), name="delete"),
]