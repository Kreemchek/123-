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
            'description': 'Для статей используйте поле "Превью" для загрузки изображения'
        }),
        ('Публикация', {
            'fields': ('is_featured', 'is_published', 'created_at', 'updated_at'),
        }),
    )

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj and obj.media_type == 'article':
            fieldsets = list(fieldsets)
            fieldsets[1] = ('Медиа-контент', {
                'fields': ('external_url', 'thumbnail', 'preview_thumbnail', 'preview_media'),
                'description': 'Для статей используйте поле "Превью" для загрузки изображения'
            })
        return fieldsets

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.media_type == 'article':
            form.base_fields['media_file'].required = False
        return form

    def preview_thumbnail(self, obj):
        if obj.thumbnail_url:
            return format_html('<img src="{}" width="150" />', obj.thumbnail_url)
        return "-"

    preview_thumbnail.short_description = 'Превью'

    def preview_media(self, obj):
        if obj.media_type == 'video':
            if obj.external_url and not obj.media_file:
                # Превью для внешних видео
                video_data = obj.get_external_video_type()
                if video_data:
                    if video_data['type'] == 'youtube':
                        return format_html(
                            '<div style="position: relative; width: 300px; height: 200px; background: #f0f0f0; border-radius: 8px; display: flex; align-items: center; justify-content: center;">'
                            '<i class="fab fa-youtube" style="font-size: 48px; color: #ff0000;"></i>'
                            '<div style="position: absolute; bottom: 8px; left: 8px; background: rgba(0,0,0,0.7); color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">YouTube</div>'
                            '</div>'
                        )
                    elif video_data['type'] == 'vk':
                        return format_html(
                            '<div style="position: relative; width: 300px; height: 200px; background: #f0f0f0; border-radius: 8px; display: flex; align-items: center; justify-content: center;">'
                            '<i class="fab fa-vk" style="font-size: 48px; color: #4a76a8;"></i>'
                            '<div style="position: absolute; bottom: 8px; left: 8px; background: rgba(0,0,0,0.7); color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">VK Video</div>'
                            '</div>'
                        )
                    elif video_data['type'] == 'rutube':
                        return format_html(
                            '<div style="position: relative; width: 300px; height: 200px; background: #f0f0f0; border-radius: 8px; display: flex; align-items: center; justify-content: center;">'
                            '<i class="fas fa-play-circle" style="font-size: 48px; color: #ff2f2f;"></i>'
                            '<div style="position: absolute; bottom: 8px; left: 8px; background: rgba(0,0,0,0.7); color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">Rutube</div>'
                            '</div>'
                        )

            # Локальное видео
            return format_html(
                '<div class="relative">'
                '<img src="{}" width="300" />'
                '<div class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">'
                '<i class="fas fa-play-circle text-white text-4xl bg-black bg-opacity-50 rounded-full"></i>'
                '</div>'
                '</div>',
                obj.thumbnail_url or ''
            )
        elif obj.media_type == 'article' and obj.thumbnail_url:
            return format_html('<img src="{}" width="300" />', obj.thumbnail_url)
        elif obj.media_file and obj.thumbnail_url:
            return format_html('<img src="{}" width="300" />', obj.thumbnail_url)
        return "-"

    preview_media.short_description = 'Медиа'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(author=request.user)