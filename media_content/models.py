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
        resource_type='auto',  # Автоопределение типа
        blank=True,
        null=True
    )

    thumbnail = CloudinaryField(
        'Превью',
        resource_type='auto',  # Изменено с 'image' на 'auto'
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

    def get_thumbnail_url(self):
        if self.thumbnail:
            # Если есть явно загруженное превью
            if hasattr(self.thumbnail, 'url'):
                return self.thumbnail.url
            return cloudinary_url(self.thumbnail.public_id)[0]
        elif self.media_file and self.media_file.resource_type == 'video':
            # Генерируем превью для видео
            return cloudinary_url(
                self.media_file.public_id,
                format="jpg",
                resource_type="video",
                transformation=[
                    {'width': 800, 'height': 600, 'crop': 'fill'},
                    {'quality': 'auto'}
                ]
            )[0]
        # Для изображений возвращаем основной файл
        elif self.media_file and self.media_file.resource_type == 'image':
            return cloudinary_url(self.media_file.public_id)[0]
        return None

    @property
    def file_url(self):
        """Возвращает правильный URL для медиа с учетом Cloudinary"""
        if self.media_file:
            if hasattr(self.media_file, 'url'):
                # Если это CloudinaryField
                if self.media_type == 'video':
                    # Для видео генерируем URL с правильным resource_type
                    url, options = cloudinary_url(
                        self.media_file.public_id,
                        resource_type="video",
                        format="mp4"
                    )
                    return url
                elif self.media_type == 'photo':
                    # Для фото используем стандартный URL с возможными преобразованиями
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
            # Генерируем превью для видео из Cloudinary
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
        return None


    def save(self, *args, **kwargs):
        # Флаг для первого сохранения
        first_save = not self.pk

        # Первое сохранение - только загрузка файла
        if first_save:
            # Сохраняем без обработки превью
            super().save(*args, **kwargs)

            # Если это видео - создаем превью
            if (self.media_file and
                    hasattr(self.media_file, 'resource_type') and
                    self.media_file.resource_type == 'video' and
                    not self.thumbnail):

                try:
                    # Генерируем превью из видео
                    thumbnail_url = cloudinary_url(
                        self.media_file.public_id,
                        format="jpg",
                        transformation=[
                            {'width': 800, 'height': 600, 'crop': 'limit'},
                            {'quality': 'auto'},
                            {'flags': 'splice', 'resource_type': 'video'}
                        ]
                    )[0]

                    # Скачиваем превью
                    response = requests.get(thumbnail_url)
                    if response.status_code == 200:
                        img = Image.open(BytesIO(response.content))
                        img_io = BytesIO()
                        img.save(img_io, format='JPEG', quality=85)

                        # Сохраняем превью
                        self.thumbnail.save(
                            f"{self.media_file.public_id}_thumbnail.jpg",
                            ContentFile(img_io.getvalue()),
                            save=False
                        )
                        # Сохраняем модель с превью
                        super().save(*args, **kwargs)

                except Exception as e:
                    logger.error(f"Ошибка при создании превью: {e}", exc_info=True)
        else:
            # Обычное сохранение для существующих записей
            super().save(*args, **kwargs)