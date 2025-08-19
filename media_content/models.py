from cloudinary import uploader
from cloudinary.utils import cloudinary_url
import requests
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image
from cloudinary.models import CloudinaryField
from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
import logging
import re

logger = logging.getLogger(__name__)
User = get_user_model()


class MediaItem(models.Model):
    MEDIA_TYPES = (
        ('video', 'Видео'),
        ('photo', 'Фото'),
        ('file', 'Файл'),
        ('article', 'Статья'),
    )

    title = models.CharField('Название', max_length=255)
    description = models.TextField('Описание', blank=True)
    media_type = models.CharField('Тип медиа', max_length=10, choices=MEDIA_TYPES)

    # Основное поле для медиа (используем Cloudinary)
    media_file = CloudinaryField(
        'Медиафайл',
        resource_type='auto',
        blank=True,
        null=True
    )

    thumbnail = CloudinaryField(
        'Превью',
        resource_type='auto',
        blank=True,
        null=True
    )

    external_url = models.URLField('Внешняя ссылка', blank=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Автор')
    is_featured = models.BooleanField('Рекомендуемый (отображать на главной)', default=False)
    is_published = models.BooleanField('Опубликовано', default=True)

    class Meta:
        verbose_name = 'Медиа'
        verbose_name_plural = 'Медиа'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('media_content:detail', kwargs={'pk': self.pk})

    def get_file_type(self):
        if self.media_file:
            return self.media_file.resource_type
        return None

    def get_external_video_type(self):
        """Определяет тип внешнего видео по URL"""
        if not self.external_url:
            return None

        # YouTube
        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([^&]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([^&]+)'
        ]
        for pattern in youtube_patterns:
            match = re.search(pattern, self.external_url)
            if match:
                return {'type': 'youtube', 'id': match.group(1)}

        # VK - исправленные регулярные выражения
        vk_patterns = [
            r'(?:https?://)?(?:www\.)?vk\.com/video(-?\d+)_(\d+)',
            r'(?:https?://)?(?:www\.)?vk\.com/video\?z=video(-?\d+)_(\d+)',
            r'(?:https?://)?(?:www\.)?vkvideo\.ru/video(-?\d+)_(\d+)',  # Добавлен vkvideo.ru
            r'(?:https?://)?(?:www\.)?vk\.com/video_ext\.php\?oid=(-?\d+)&id=(\d+)'  # Для прямых ссылок
        ]
        for pattern in vk_patterns:
            match = re.search(pattern, self.external_url)
            if match:
                return {'type': 'vk', 'owner_id': match.group(1), 'video_id': match.group(2)}

        # Rutube - исправленные регулярные выражения
        rutube_patterns = [
            r'(?:https?://)?(?:www\.)?rutube\.ru/video/([a-f0-9]+)/',
            r'(?:https?://)?(?:www\.)?rutube\.ru/play/embed/([a-f0-9]+)',
            r'(?:https?://)?(?:www\.)?rutube\.ru/video/([a-f0-9]+)',  # Без слеша в конце
            r'(?:https?://)?(?:www\.)?rutube\.ru/video/([a-f0-9]+)/?\??'  # С возможными параметрами
        ]
        for pattern in rutube_patterns:
            match = re.search(pattern, self.external_url)
            if match:
                return {'type': 'rutube', 'id': match.group(1)}

        return None

    @property
    def is_external_video(self):
        """Проверяет, является ли медиа внешним видео"""
        return self.media_type == 'video' and self.external_url and not self.media_file

    @property
    def external_video_data(self):
        """Возвращает данные внешнего видео"""
        return self.get_external_video_type()

    def get_thumbnail_url(self):
        if self.thumbnail:
            if hasattr(self.thumbnail, 'url'):
                return self.thumbnail.url
            return cloudinary_url(self.thumbnail.public_id)[0]
        elif self.media_file and self.media_file.resource_type == 'video':
            return cloudinary_url(
                self.media_file.public_id,
                format="jpg",
                resource_type="video",
                transformation=[
                    {'width': 800, 'height': 600, 'crop': 'fill'},
                    {'quality': 'auto'}
                ]
            )[0]
        elif self.media_file and self.media_file.resource_type == 'image':
            return cloudinary_url(self.media_file.public_id)[0]
        elif self.media_type == 'article' and self.thumbnail:
            return self.thumbnail.url
        return None

    @property
    def file_url(self):
        """Возвращает правильный URL для медиа с учетом Cloudinary"""
        if self.media_file:
            if hasattr(self.media_file, 'url'):
                if self.media_type == 'video':
                    url, options = cloudinary_url(
                        self.media_file.public_id,
                        resource_type="video",
                        format="mp4"
                    )
                    return url
                elif self.media_type == 'photo':
                    url, options = cloudinary_url(
                        self.media_file.public_id,
                        format="jpg",
                        quality="auto",
                        fetch_format="auto"
                    )
                    return url
                return self.media_file.url
            return self.media_file.url
        return None

    @property
    def thumbnail_url(self):
        """Возвращает URL превью с учетом Cloudinary"""
        if self.thumbnail:
            if hasattr(self.thumbnail, 'url'):
                return self.thumbnail.url
            return self.thumbnail.url
        elif self.media_type == 'video' and self.media_file:
            url, options = cloudinary_url(
                self.media_file.public_id,
                resource_type="video",
                format="jpg",
                transformation=[
                    {'width': 800, 'height': 600, 'crop': 'fill'},
                    {'quality': 'auto'}
                ]
            )
            return url
        elif self.media_type == 'article' and self.thumbnail:
            return self.thumbnail.url
        return None

    def save(self, *args, **kwargs):
        first_save = not self.pk

        if first_save:
            super().save(*args, **kwargs)

            if (self.media_file and
                    hasattr(self.media_file, 'resource_type') and
                    self.media_file.resource_type == 'video' and
                    not self.thumbnail):

                try:
                    thumbnail_url = cloudinary_url(
                        self.media_file.public_id,
                        format="jpg",
                        transformation=[
                            {'width': 800, 'height': 600, 'crop': 'limit'},
                            {'quality': 'auto'},
                            {'flags': 'splice', 'resource_type': 'video'}
                        ]
                    )[0]

                    response = requests.get(thumbnail_url)
                    if response.status_code == 200:
                        img = Image.open(BytesIO(response.content))
                        img_io = BytesIO()
                        img.save(img_io, format='JPEG', quality=85)

                        self.thumbnail.save(
                            f"{self.media_file.public_id}_thumbnail.jpg",
                            ContentFile(img_io.getvalue()),
                            save=False
                        )
                        super().save(*args, **kwargs)

                except Exception as e:
                    logger.error(f"Ошибка при создании превью: {e}", exc_info=True)
        else:
            super().save(*args, **kwargs)