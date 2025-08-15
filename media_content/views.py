from django.views.generic import ListView, DetailView
from .models import MediaItem

class MediaListView(ListView):
    model = MediaItem
    template_name = 'media/list.html'
    context_object_name = 'media_items'
    paginate_by = 12

    def get_queryset(self):
        return MediaItem.objects.filter(is_published=True)

class MediaDetailView(DetailView):
    model = MediaItem
    template_name = 'media/detail.html'
    context_object_name = 'media_item'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['related_items'] = MediaItem.objects.filter(
            media_type=self.object.media_type,
            is_published=True
        ).exclude(pk=self.object.pk)[:4]
        return context