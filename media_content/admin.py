from django.contrib import admin
from django.utils.html import format_html
from .models import MediaItem

@admin.register(MediaItem)
class MediaItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'media_type', 'author', 'created_at', 'is_featured',
                   'is_published', 'preview_thumbnail', 'preview_media')
    list_filter = ('media_type', 'is_featured', 'is_published', 'created_at')
    search_fields = ('title', 'description', 'author__username')
    list_editable = ('is_featured', 'is_published')
    readonly_fields = ('created_at', 'updated_at', 'author',
                      'preview_thumbnail', 'preview_media')

    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'media_type', 'author')
        }),
        ('Медиа-контент', {
            'fields': ('media_file', 'external_url', 'thumbnail',
                      'preview_thumbnail', 'preview_media'),
            'description': 'Загружайте видео или изображения в поле "Медиафайл"'
        }),
        ('Публикация', {
            'fields': ('is_featured', 'is_published', 'created_at', 'updated_at'),
        }),
    )


    def preview_thumbnail(self, obj):
        if obj.thumbnail:
            if hasattr(obj.thumbnail, 'resource_type'):
                if obj.thumbnail.resource_type == 'image':
                    return format_html('<img src="{}" width="150" />', obj.thumbnail.url)
                return "Файл не является изображением"
            return format_html('<img src="{}" width="150" />', obj.thumbnail.url)
        return "-"

    def preview_media(self, obj):
        if obj.media_file:
            if obj.media_file.resource_type == 'video':
                # Используем новый метод thumbnail_url
                return format_html(
                    '<div class="relative">'
                    '<img src="{}" width="300" />'
                    '<div class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">'
                    '<i class="fas fa-play-circle text-white text-4xl bg-black bg-opacity-50 rounded-full"></i>'
                    '</div>'
                    '</div>',
                    obj.thumbnail_url or ''
                )
            else:
                return format_html('<img src="{}" width="300" />', obj.thumbnail_url or '')
        return "-"

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(author=request.user)