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
                        # Для VK клипов и видео
                        badge_text = 'VK Clip' if video_data.get(
                            'is_clip') or 'clip' in obj.external_url else 'VK Video'
                        return format_html(
                            '<div style="position: relative; width: 300px; height: 200px; background: #f0f0f0; border-radius: 8px; display: flex; align-items: center; justify-content: center;">'
                            '<i class="fab fa-vk" style="font-size: 48px; color: #4a76a8;"></i>'
                            '<div style="position: absolute; bottom: 8px; left: 8px; background: rgba(0,0,0,0.7); color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">{}</div>'
                            '</div>',
                            badge_text
                        )
                    elif video_data['type'] == 'rutube':
                        return format_html(
                            '<div style="position: relative; width: 300px; height: 200px; background: #f0f0f0; border-radius: 8px; display: flex; align-items: center; justify-content: center;">'
                            '<i class="fas fa-play-circle" style="font-size: 48px; color: #ff2f2f;"></i>'
                            '<div style="position: absolute; bottom: 8px; left: 8px; background: rgba(0,0,0,0.7); color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">Rutube</div>'
                            '</div>'
                        )
                    else:
                        return format_html(
                            '<div style="position: relative; width: 300px; height: 200px; background: #f0f0f0; border-radius: 8px; display: flex; align-items: center; justify-content: center;">'
                            '<i class="fas fa-video" style="font-size: 48px; color: #666;"></i>'
                            '<div style="position: absolute; bottom: 8px; left: 8px; background: rgba(0,0,0,0.7); color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">Внешнее видео</div>'
                            '</div>'
                        )

            # Локальное видео
            if obj.thumbnail_url:
                return format_html(
                    '<div style="position: relative; display: inline-block;">'
                    '<img src="{}" width="300" style="border-radius: 8px;" />'
                    '<div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);">'
                    '<i class="fas fa-play-circle" style="font-size: 48px; color: white; text-shadow: 0 2px 8px rgba(0,0,0,0.7);"></i>'
                    '</div>'
                    '</div>',
                    obj.thumbnail_url
                )
            else:
                return format_html(
                    '<div style="position: relative; width: 300px; height: 200px; background: #f0f0f0; border-radius: 8px; display: flex; align-items: center; justify-content: center;">'
                    '<i class="fas fa-video" style="font-size: 48px; color: #999;"></i>'
                    '<div style="position: absolute; bottom: 8px; left: 8px; background: rgba(0,0,0,0.7); color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">Локальное видео</div>'
                    '</div>'
                )

        elif obj.media_type == 'photo':
            if obj.thumbnail_url:
                return format_html('<img src="{}" width="300" style="border-radius: 8px;" />', obj.thumbnail_url)
            elif obj.file_url:
                return format_html('<img src="{}" width="300" style="border-radius: 8px;" />', obj.file_url)
            else:
                return format_html(
                    '<div style="width: 300px; height: 200px; background: #f0f0f0; border-radius: 8px; display: flex; align-items: center; justify-content: center;">'
                    '<i class="fas fa-image" style="font-size: 48px; color: #999;"></i>'
                    '</div>'
                )

        elif obj.media_type == 'article':
            if obj.thumbnail_url:
                return format_html(
                    '<div style="position: relative;">'
                    '<img src="{}" width="300" style="border-radius: 8px;" />'
                    '<div style="position: absolute; bottom: 8px; left: 8px; background: rgba(0,0,0,0.7); color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">Статья</div>'
                    '</div>',
                    obj.thumbnail_url
                )
            else:
                return format_html(
                    '<div style="position: relative; width: 300px; height: 200px; background: #f0f0f0; border-radius: 8px; display: flex; align-items: center; justify-content: center;">'
                    '<i class="fas fa-newspaper" style="font-size: 48px; color: #999;"></i>'
                    '<div style="position: absolute; bottom: 8px; left: 8px; background: rgba(0,0,0,0.7); color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">Статья</div>'
                    '</div>'
                )

        elif obj.media_type == 'file':
            return format_html(
                '<div style="width: 300px; height: 200px; background: #f0f0f0; border-radius: 8px; display: flex; align-items: center; justify-content: center; flex-direction: column;">'
                '<i class="fas fa-file-alt" style="font-size: 48px; color: #999; margin-bottom: 16px;"></i>'
                '<div style="background: rgba(0,0,0,0.7); color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">Файл</div>'
                '</div>'
            )

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