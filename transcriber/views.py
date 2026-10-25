from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView,
)

from .models import Transcription


class TranscriptionListView(ListView):
    model = Transcription
    paginate_by = 10
    context_object_name = "transcriptions"

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(text__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        return context


class TranscriptionDetailView(DetailView):
    model = Transcription


class TranscriptionCreateView(CreateView):
    model = Transcription
    fields = ["title", "text", "language"]
    success_url = reverse_lazy("transcriber:list")


class TranscriptionUpdateView(UpdateView):
    model = Transcription
    fields = ["title", "text", "language"]
    success_url = reverse_lazy("transcriber:list")


class TranscriptionDeleteView(DeleteView):
    model = Transcription
    success_url = reverse_lazy("transcriber:list")