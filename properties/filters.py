import re  # Добавьте эту строку в начало файла
from django import forms
from django.db.models import Q
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django_filters import FilterSet, NumberFilter, CharFilter, BooleanFilter, ModelMultipleChoiceFilter
from .models import Property, PropertyType, CityCenter


class PropertyFilter(FilterSet):
    # Существующие фильтры
    min_price = NumberFilter(field_name='price', lookup_expr='gte')
    max_price = NumberFilter(field_name='price', lookup_expr='lte')
    min_price_per_sqm = NumberFilter(method='filter_price_per_sqm')
    max_price_per_sqm = NumberFilter(method='filter_price_per_sqm')

    # Площадь
    min_area = NumberFilter(field_name='total_area', lookup_expr='gte')
    max_area = NumberFilter(field_name='total_area', lookup_expr='lte')
    min_living_area = NumberFilter(field_name='living_area', lookup_expr='gte')
    max_living_area = NumberFilter(field_name='living_area', lookup_expr='lte')

    # Комнаты
    rooms = NumberFilter(field_name='rooms')
    rooms__gte = NumberFilter(field_name='rooms', lookup_expr='gte')
    rooms__lte = NumberFilter(field_name='rooms', lookup_expr='lte')

    # Этажи
    min_floor = NumberFilter(field_name='floor', lookup_expr='gte')
    max_floor = NumberFilter(field_name='floor', lookup_expr='lte')
    min_total_floors = NumberFilter(field_name='total_floors', lookup_expr='gte')
    max_total_floors = NumberFilter(field_name='total_floors', lookup_expr='lte')

    # Год постройки
    min_construction_year = NumberFilter(field_name='construction_year', lookup_expr='gte')
    max_construction_year = NumberFilter(field_name='construction_year', lookup_expr='lte')

    # Расстояние до центра
    min_distance_to_center = NumberFilter(method='filter_by_distance_to_center')
    max_distance_to_center = NumberFilter(method='filter_by_distance_to_center')

    # Тип недвижимости
    property_type = ModelMultipleChoiceFilter(
        queryset=PropertyType.objects.all(),
        widget=forms.CheckboxSelectMultiple
    )

    # Метро, город
    metro_station = CharFilter(field_name='metro_station', lookup_expr='icontains')
    location = CharFilter(field_name='location', lookup_expr='icontains')

    # Дополнительные параметры
    has_finishing = BooleanFilter(field_name='has_finishing', widget=forms.CheckboxInput)
    is_delivered = BooleanFilter(field_name='is_delivered', widget=forms.CheckboxInput)

    # Поиск по радиусу
    radius_filter = CharFilter(method='filter_by_radius')

    # Поиск по застройщику/брокеру
    developer = CharFilter(field_name='developer__id')
    broker = CharFilter(field_name='broker__id')

    class Meta:
        model = Property
        fields = [
            'property_type', 'rooms', 'location',
            'metro_station', 'has_finishing', 'is_delivered'
        ]
    def filter_price_per_sqm(self, queryset, name, value):
        if value:
            if name == 'min_price_per_sqm':
                return queryset.filter(price_per_sqm__gte=value)
            elif name == 'max_price_per_sqm':
                return queryset.filter(price_per_sqm__lte=value)
        return queryset

        # Обновляем фильтр расстояния до центра

    def filter_by_distance_to_center(self, queryset, name, value):
        if not value:
            return queryset

        try:
            value = float(value)
            # Получаем все города из выборки
            locations = queryset.values_list('location', flat=True).distinct()

            # Создаем Q-объект для фильтрации
            q_objects = Q()

            for city in locations:
                city_center = CityCenter.objects.filter(city__iexact=city).first()
                if city_center:
                    if name == 'min_distance_to_center':
                        q_objects |= Q(
                            location=city,
                            coordinates__distance_gte=(city_center.coordinates, D(km=value))
                        )
                    elif name == 'max_distance_to_center':
                        q_objects |= Q(
                            location=city,
                            coordinates__distance_lte=(city_center.coordinates, D(km=value))
                        )

            return queryset.filter(q_objects).annotate(
                distance=Distance('coordinates', city_center.coordinates)
            )

        except (ValueError, TypeError):
            return queryset

    def filter_by_radius(self, queryset, name, value):
        try:
            if value:
                parts = value.split(',')
                if len(parts) == 3:
                    lat, lon, radius = map(float, parts)
                    center = Point(lon, lat, srid=4326)
                    return queryset.filter(
                        coordinates__distance_lte=(center, D(km=radius))
                    ).annotate(
                        distance=Distance('coordinates', center)
                    ).order_by('distance')
        except (ValueError, IndexError):
            pass
        return queryset

    search = CharFilter(method='universal_search', label='Универсальный поиск')

    def universal_search(self, queryset, name, value):
        print(f"Universal search triggered with value: {value}")
        if not value:
            return queryset

        # Обработка специальных запросов (цена, площадь)
        value = re.sub(r'цена\s*(\d+)\s*-\s*(\d+)\s*млн',
                       lambda m: f"{m.group(1)}000000 {m.group(2)}000000", value, flags=re.IGNORECASE)
        value = re.sub(r'площадь\s*(\d+)\s*-\s*(\d+)\s*м²',
                       lambda m: f"{m.group(1)} {m.group(2)}", value, flags=re.IGNORECASE)

        search_terms = re.findall(r'(?:"([^"]+)"|(\S+))', value)
        search_terms = [term[0] or term[1] for term in search_terms]

        q_objects = Q()

        for term in search_terms:
            # Поиск по типам недвижимости
            type_mapping = {
                'квартира': 'apartment',
                'дом': 'house',
                'коммерческая': 'commercial',
                'новостройка': 'new_flat',
                'вторичка': 'resale_flat'
            }
            if term.lower() in type_mapping:
                q_objects |= Q(property_type__name=type_mapping[term.lower()])
                continue

            # Попробуем преобразовать в число (для комнат, площади, цены)
            try:
                numeric_term = float(term.replace(',', '.'))
                q_objects |= (
                        Q(rooms=numeric_term) |
                        Q(total_area=numeric_term) |
                        Q(living_area=numeric_term) |
                        Q(price=numeric_term) |
                        Q(monthly_price=numeric_term) |
                        Q(daily_price=numeric_term))
                continue
            except ValueError:
                pass

            # Текстовый поиск по всем полям
            q_objects |= (
                    Q(title__icontains=term) |
                    Q(description__icontains=term) |
                    Q(location__icontains=term) |
                    Q(address__icontains=term) |
                    Q(metro_station__icontains=term) |
                    Q(property_type__name__icontains=term)
            )

        return queryset.filter(q_objects).distinct()