from django import forms
from django.db.models import Q
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django_filters import FilterSet, NumberFilter, CharFilter, BooleanFilter, ModelMultipleChoiceFilter
from .models import Property, PropertyType


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

    # Метро, район, город
    metro_station = CharFilter(field_name='metro_station', lookup_expr='icontains')
    district = CharFilter(field_name='district', lookup_expr='icontains')
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
            'property_type', 'rooms', 'location', 'district',
            'metro_station', 'has_finishing', 'is_delivered'
        ]

    def filter_price_per_sqm(self, queryset, name, value):
        if value:
            if name == 'min_price_per_sqm':
                return queryset.filter(price_per_sqm__gte=value)
            elif name == 'max_price_per_sqm':
                return queryset.filter(price_per_sqm__lte=value)
        return queryset

    def filter_by_distance_to_center(self, queryset, name, value):
        # Реализация расчета расстояния до центра
        if value and name == 'min_distance_to_center':
            return queryset.filter(distance_to_center__gte=value)
        elif value and name == 'max_distance_to_center':
            return queryset.filter(distance_to_center__lte=value)
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