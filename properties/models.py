from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from cloudinary.models import CloudinaryField
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
import logging
import requests
from django.conf import settings
from django.core.exceptions import ValidationError
logger = logging.getLogger('properties')
class PropertyType(models.Model):
    name = models.CharField(
        max_length=100,
        choices=[
            ('new_flat', 'Новостройка'),
            ('resale_flat', 'Вторичка'),
            ('commercial', 'Нежилое помещение'),
            ('house', 'Дом')
        ],
        unique=True,
        verbose_name='Тип объекта'
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Описание')
    )
    icon = models.CharField(
        max_length=50,
        default='home',
        choices=[
            ('building', 'Здание'),
            ('home', 'Дом'),
            ('warehouse', 'Склад'),
            ('city', 'Город')
        ]
    )

    class Meta:
        verbose_name = _('Тип недвижимости')
        verbose_name_plural = _('Типы недвижимости')
        ordering = ['name']

    def __str__(self):
        return self.name

class Property(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Активно')
        SOLD = 'sold', _('Продано')
        ARCHIVED = 'archived', _('В архиве')

    IS_RENTAL_CHOICES = [
        ('no', 'Не арендное'),
        ('monthly', 'Аренда помесячно'),
        ('daily', 'Аренда посуточно'),
    ]
    is_rental = models.CharField(
        max_length=10,
        choices=IS_RENTAL_CHOICES,
        default='no',
        verbose_name=_('Тип аренды')
    )

    title = models.CharField(max_length=200, blank=True, verbose_name=_('Заголовок'))
    description = models.TextField(verbose_name=_('Описание'))
    property_type = models.ForeignKey(
        PropertyType,
        on_delete=models.PROTECT,
        verbose_name=_('Тип недвижимости')
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Цена'),
        null=True,  # Добавьте это
        blank=True,  # И это
        default=None
    )

    monthly_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Цена за месяц'),
        null=True,
        blank=True,
        default=None
    )
    daily_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Цена за сутки'),
        null=True,
        blank=True,
        default=None
    )
    rooms = models.PositiveIntegerField(verbose_name=_('Количество комнат'))
    location = models.CharField(max_length=200, verbose_name=_('Расположение'))
    address = models.TextField(verbose_name=_('Полный адрес'))
    main_image = CloudinaryField('main_image', blank=True, null=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name=_('Статус')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Дата обновления'))
    broker = models.ForeignKey(
        'brokers.BrokerProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='properties',
        verbose_name=_('Брокер')
    )
    developer = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='developer_properties',
        verbose_name=_('Застройщик')
    )
    is_premium = models.BooleanField(default=False, verbose_name=_('Премиум'))
    is_hot = models.BooleanField(default=False, verbose_name=_('Горячее предложение'))
    is_approved = models.BooleanField(default=False, verbose_name=_('Одобрено'))
    floor = models.PositiveIntegerField(
        verbose_name=_('Этаж'),
        blank=True,
        null=True,
        validators=[MinValueValidator(1)]
    )
    total_floors = models.PositiveIntegerField(
        verbose_name=_('Всего этажей в доме'),
        validators=[MinValueValidator(1)],
        null=True,
        blank=True
    )
    apartment_type = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ('studio', 'Студия'),
            ('apartment', 'Апартаменты'),
            ('regular', 'Обычная квартира'),
        ],
        verbose_name=_('Тип квартиры')
    )
    has_finishing = models.BooleanField(verbose_name='Отделка', default=False)
    delivery_year = models.PositiveIntegerField(
        verbose_name='Год сдачи',
        null=True,
        blank=True
    )
    construction_year = models.PositiveIntegerField(
        verbose_name='Год постройки',
        null=True,
        blank=True
    )
    distance_to_center = models.FloatField(
        verbose_name='Расстояние до центра (км)',
        null=True,
        blank=True
    )

    is_delivered = models.BooleanField(verbose_name='Дом сдан', default=False)
    living_area = models.DecimalField(
        verbose_name='Жилая площадь (м²)',
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )
    total_area = models.DecimalField(
        verbose_name='Общая площадь (м²)',
        max_digits=8,
        decimal_places=2,
        default=0.00
    )
    metro_station = models.CharField(
        verbose_name='Станция метро',
        max_length=100,
        blank=True
    )
    coordinates = gis_models.PointField(
        geography=True,
        blank=True,
        null=True,
        verbose_name='Координаты'
    )
    metro_coordinates = gis_models.PointField(
        geography=True,
        blank=True,
        null=True,
        verbose_name='Координаты метро'
    )

    # Метод для геокодирования адреса
    # В models.py
    def geocode_address(self):
        try:
            # Используем API Поиска для более точных результатов
            search_url = (
                f"https://search-maps.yandex.ru/v1/"
                f"?apikey={settings.YANDEX_SEARCH_API_KEY}"
                f"&text={self.address}"
                f"&lang=ru_RU"
                f"&results=1"
            )
            search_response = requests.get(search_url)

            if search_response.status_code == 200:
                data = search_response.json()
                if data.get('features'):
                    feature = data['features'][0]
                    lon, lat = feature['geometry']['coordinates']
                    self.coordinates = Point(lon, lat, srid=4326)
                    return

            # Fallback на обычный геокодер
            geocoder_url = (
                f"https://geocode-maps.yandex.ru/1.x/"
                f"?apikey={settings.YANDEX_GEOCODER_API_KEY}"
                f"&format=json"
                f"&geocode={self.address}"
            )
            response = requests.get(geocoder_url)
            data = response.json()

            if data['response']['GeoObjectCollection']['metaDataProperty']['GeocoderResponseMetaData']['found'] > 0:
                pos = data['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos']
                lon, lat = map(float, pos.split())
                self.coordinates = Point(lon, lat, srid=4326)

        except Exception as e:
            logger.error(f"Geocoding failed for address {self.address}: {str(e)}")

    def get_coordinates_as_floats(self):
        """Возвращает координаты как числа с плавающей точкой"""
        if self.coordinates:
            return {
                'x': float(self.coordinates.x),
                'y': float(self.coordinates.y)
            }
        return None

        # Метод для обновления расстояния до центра

    def update_distance_to_center(self):
        """
        Рассчитывает расстояние до центра города в километрах.
        Возвращает расстояние или None, если не удалось рассчитать.
        """
        if not self.coordinates or not self.location:
            return None

        try:
            # Получаем центр города из базы данных
            city_center = CityCenter.objects.filter(city__iexact=self.location).first()
            if not city_center:
                # Если центр города не задан, попробуем найти его через геокодер
                center_coords = self._geocode_city_center(self.location)
                if center_coords:
                    city_center = CityCenter.objects.create(
                        city=self.location,
                        coordinates=Point(center_coords[0], center_coords[1], srid=4326)
                    )
                else:
                    return None

            # Вычисляем расстояние (примерно в км) и возвращаем значение
            distance = self.coordinates.distance(city_center.coordinates) * 100
            return distance

        except Exception as e:
            logger.error(f"Error calculating distance to center: {str(e)}")
            return None

    def _geocode_city_center(self, city_name):
        """Геокодирование центра города через Яндекс API"""
        try:
            url = f"https://geocode-maps.yandex.ru/1.x/?apikey={settings.YANDEX_GEOCODER_API_KEY}&format=json&geocode={city_name}&kind=locality"
            response = requests.get(url)
            data = response.json()

            if data['response']['GeoObjectCollection']['metaDataProperty']['GeocoderResponseMetaData']['found'] > 0:
                pos = data['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos']
                lon, lat = map(float, pos.split())
                return (lon, lat)
        except Exception as e:
            logger.error(f"Geocoding error for city {city_name}: {str(e)}")
        return None


    class Meta:
        verbose_name = _('Объект недвижимости')
        verbose_name_plural = _('Объекты недвижимости')
        ordering = ['-created_at']


    def __str__(self):
        if self.is_rental == 'monthly' and self.monthly_price:
            return f"{self.title} - {self.monthly_price} ₽/мес"
        elif self.is_rental == 'daily' and self.daily_price:
            return f"{self.title} - {self.daily_price} ₽/сут"
        return f"{self.title} - {self.price} ₽"



    def get_status_color(self):
        colors = {
            'active': 'green',
            'sold': 'red',
            'archived': 'gray'
        }
        return colors.get(self.status, 'blue')

    def save(self, *args, **kwargs):
        # Генерация заголовка
        if self.property_type.name in ['new_flat', 'resale_flat']:
            type_map = {
                'studio': 'Студия',
                'apartment': 'Апартаменты',
                'regular': f'{self.rooms}-к. квартира'
            }

            floor_info = str(self.floor) if self.floor else ''
            if self.floor and self.total_floors:
                floor_info = f"{self.floor}/{self.total_floors}"

            parts = [
                type_map.get(self.apartment_type, 'Квартира'),
                f"{self.total_area} м²",
                f"{floor_info} этаж" if floor_info else None,
            ]
            self.title = ", ".join(filter(None, parts))
        elif self.property_type.name == 'house':
            self.title = f"Дом, {self.total_area} м²"
        else:
            self.title = f"{self.property_type.get_name_display()}, {self.total_area} м²"

        # Обновление расстояния до центра
        if self.coordinates and self.location:
            self.distance_to_center = self.update_distance_to_center()

        # Валидация координат
        if self.coordinates:
            logger.debug(f"Saving coordinates: x={self.coordinates.x}, y={self.coordinates.y}")
            if not (-180 <= self.coordinates.x <= 180) or not (-90 <= self.coordinates.y <= 90):
                raise ValidationError("Некорректные координаты")

        # Вызов оригинального метода save
        super().save(*args, **kwargs)

        # Метод для получения ближайшего метро

    def get_nearest_metro(self):
        import requests
        from django.conf import settings

        if not self.coordinates or not settings.YANDEX_MAPS_API_KEY:
            return None

        try:
            lon, lat = self.coordinates.coords
            url = f"https://geocode-maps.yandex.ru/1.x/?apikey={settings.YANDEX_MAPS_API_KEY}&format=json&geocode={lon},{lat}&kind=metro"
            response = requests.get(url)
            data = response.json()

            metro = data['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['name']
            return metro
        except Exception as e:
            print(f"Metro search error: {e}")
            return None

    def get_metro_coordinates(self):
        import requests
        from django.conf import settings

        if not self.metro_station or not settings.YANDEX_GEOCODER_API_KEY:
            return None

        try:
            url = f"https://geocode-maps.yandex.ru/1.x/?apikey={settings.YANDEX_GEOCODER_API_KEY}&format=json&geocode={self.metro_station}&kind=metro"
            response = requests.get(url)
            data = response.json()

            if data['response']['GeoObjectCollection']['metaDataProperty']['GeocoderResponseMetaData']['found'] > 0:
                pos = data['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos']
                lon, lat = map(float, pos.split())
                return Point(lon, lat, srid=4326)
        except Exception as e:
            print(f"Metro geocoding error: {e}")

        return None

    def clean(self):
        if self.coordinates:
            # Проверяем порядок координат (x=долгота, y=широта)
            if not (-180 <= self.coordinates.x <= 180) or not (-90 <= self.coordinates.y <= 90):
                raise ValidationError("Некорректные координаты")


class CityCenter(models.Model):
    city = models.CharField(max_length=100, unique=True, verbose_name='Город')
    coordinates = gis_models.PointField(verbose_name='Координаты центра')

    class Meta:
        verbose_name = 'Центр города'
        verbose_name_plural = 'Центры городов'

    def __str__(self):
        return self.city

class PropertyImage(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name=_('Объект')
    )
    image = CloudinaryField('image', blank=True, null=True)
    order = models.PositiveIntegerField(default=0, verbose_name=_('Порядок'))
    is_main = models.BooleanField(default=False, verbose_name=_('Главное изображение'))

    class Meta:
        verbose_name = _('Изображение объекта')
        verbose_name_plural = _('Изображения объектов')
        ordering = ['order']

    def __str__(self):
        return f"Изображение для {self.property.title}"

class ListingType(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    duration_days = models.PositiveIntegerField(verbose_name='Длительность (дни)')
    is_featured = models.BooleanField(default=False, verbose_name='Премиум размещение')
    description = models.TextField(verbose_name='Описание')

    class Meta:
        verbose_name = 'Тип размещения'
        verbose_name_plural = 'Типы размещений'

    def __str__(self):
        return self.name


# models.py
class MetroStation(models.Model):
    city = models.CharField(max_length=100, verbose_name='Город')
    name = models.CharField(max_length=100, verbose_name='Название станции')
    line = models.CharField(
        max_length=100,
        verbose_name='Линия метро',
        blank=True,
        null=True
    )
    line_color = models.CharField(
        max_length=50,
        verbose_name='Цвет линии',
        blank=True,
        null=True
    )
    coordinates = gis_models.PointField(verbose_name='Координаты', srid=4326)

    class Meta:
        verbose_name = 'Станция метро'
        verbose_name_plural = 'Станции метро'
        unique_together = ('city', 'name')  # Одна станция может быть только в одном городе

    def __str__(self):
        return f"{self.name} ({self.city})"


