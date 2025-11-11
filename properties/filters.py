import re
from django import forms
from django.db.models import Q, ExpressionWrapper, F, FloatField
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django_filters import FilterSet, NumberFilter, CharFilter, BooleanFilter, ModelMultipleChoiceFilter
from .models import Property, PropertyType, CityCenter, MetroStation


class MetroStationMultipleChoiceWidget(forms.SelectMultiple):
    max_choices = 5

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update({
            'class': 'metro-station-select',
            'data-max-choices': self.max_choices
        })


class MetroStationFilter(CharFilter):
    def filter(self, qs, value):
        if not value:
            return qs

        # Разделяем строку по запятым, удаляем пробелы и пустые значения
        stations = [s.strip() for s in value.split(',') if s.strip()]
        if not stations:
            return qs

        # Создаем Q-объекты для поиска по каждой станции
        q_objects = Q()
        for station in stations:
            # Ищем полное совпадение или станцию в составе строки
            q_objects |= Q(metro_station__iexact=station) | Q(metro_station__icontains=station)

        return qs.filter(q_objects).distinct()


class PropertyFilter(FilterSet):
    # Существующие фильтры
    min_price = NumberFilter(field_name='price', lookup_expr='gte')
    max_price = NumberFilter(field_name='price', lookup_expr='lte')

    # УБРАН фильтр price_per_sqm или ЗАМЕНЕН на исправленную версию:
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

    min_construction_year = NumberFilter(field_name='delivery_year', lookup_expr='gte')
    max_construction_year = NumberFilter(field_name='delivery_year', lookup_expr='lte')

    # Расстояние до центра
    min_distance_to_center = NumberFilter(method='filter_by_distance_to_center')
    max_distance_to_center = NumberFilter(method='filter_by_distance_to_center')
    rental_type = CharFilter(method='filter_rental_type', label='Тип аренды')

    def filter_rental_type(self, queryset, name, value):
        if not value:
            return queryset

        # Обрабатываем разные форматы входящих данных
        if isinstance(value, list):
            rental_types = value
        elif ',' in value:
            rental_types = [t.strip() for t in value.split(',') if t.strip()]
        else:
            rental_types = [value]

        if not rental_types:
            return queryset

        q_objects = Q()

        for rental_type in rental_types:
            rental_type = rental_type.strip().lower()
            if rental_type == 'monthly':
                q_objects |= Q(is_rental='monthly', monthly_price__isnull=False)
            elif rental_type == 'daily':
                q_objects |= Q(is_rental='daily', daily_price__isnull=False)
            elif rental_type == 'no':
                q_objects |= Q(is_rental='no')

        return queryset.filter(q_objects).distinct() if q_objects else queryset


    # Тип недвижимости
    property_type = ModelMultipleChoiceFilter(
        field_name='property_type__name',
        queryset=PropertyType.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label='Тип недвижимости',
        to_field_name='name'
    )
    metro_station = MetroStationFilter(label='Станции метро')


    def filter_by_metro_name(self, queryset, name, value):
        if not value:
            return queryset

        stations = [s.strip() for s in value.split(',') if s.strip()]
        if not stations:
            return queryset

        q_objects = Q()
        for station in stations:
            q_objects |= Q(metro_station__icontains=station)

        return queryset.filter(q_objects).distinct()

    location = CharFilter(field_name='location', lookup_expr='icontains')

    # Дополнительные параметры
    has_finishing = BooleanFilter(
        field_name='has_finishing',
        label='Только с отделкой'
    )

    is_delivered = BooleanFilter(
        field_name='is_delivered',
        label='Только сданные'
    )

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Динамически обновляем queryset для поля metro_station на основе выбранного города
        if 'location' in self.data:
            try:
                city = self.data.get('location')
                if city:
                    self.filters['metro_station'].field.queryset = MetroStation.objects.filter(
                        city__iexact=city
                    ).order_by('name')
            except (ValueError, TypeError):
                pass

    def filter_price_per_sqm(self, queryset, name, value):
        if value:
            # Аннотируем queryset ценой за квадратный метр
            queryset = queryset.annotate(
                price_per_sqm=ExpressionWrapper(
                    F('price') / F('total_area'),
                    output_field=FloatField()
                )
            )

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
                if not city_center:
                    continue  # Пропускаем города без центра

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

            # Если нашли подходящие города, применяем фильтр и аннотацию
            if q_objects:
                # Берем первый попавшийся city_center для аннотации (в данном контексте это не критично)
                sample_city_center = CityCenter.objects.filter(
                    city__in=locations
                ).first()

                if sample_city_center:
                    return queryset.filter(q_objects).annotate(
                        distance=Distance('coordinates', sample_city_center.coordinates)
                    )

            # Если не нашли подходящих городов или центров, возвращаем пустой queryset
            return queryset.none()

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
        if not value:
            return queryset

        value = value.lower().strip()
        q_objects = Q()

        # Обработка запросов типа "2-комнатная квартира в Москве"
        room_match = re.search(r'(\d+)\s*-?\s*комнатн(ая|ые|ую|ой)', value)
        type_match = re.search(
            r'(квартир[ауеы]|студи[юя]|апартамент[ыа]|дом|коммерческ[аяой]|новостройк[аи]|вторичк[ау])', value)
        city_match = re.search(
            r'(в|на)\s+(москв[еу]|санкт\s*-?\s*петербург[е]|спб|екатеринбург[е]|новосибирск[е]|казан[и]|нижн[еий][йм]\s*новгород[е]|самар[е]|омск[е]|челябинск[е]|ростов[е]\s*-?\s*на\s*-?\s*дону|уф[е]|красноярск[е]|перм[и]|воронеж[е]|волгоград[е]|краснодар[е]|сочи|подольск|мытищ|балаших|люберц|химк|зеленоград)',
            value)
        rent_match = re.search(r'(снять|аренд[ауеы]|посуточн[аяой]|помесячн[аяой])', value)
        buy_match = re.search(r'(куп[иить]|приобрести|продаж[ае]|покупк[ае])', value)
        price_match = re.search(r'(цена|стоимость)\s*(от|до)?\s*(\d+)\s*(млн|тыс|т\.?р|р\.?)', value)
        area_match = re.search(r'(площадь|площадью|метраж)\s*(\d+)\s*-?\s*(\d+)?\s*(м|м²|кв\.?\s*м)', value)

        # Обработка количества комнат
        if room_match:
            rooms = int(room_match.group(1))
            q_objects &= Q(rooms=rooms)

        # Универсальная обработка типа недвижимости
        type_mapping = {
            'квартир': ['new_flat', 'resale_flat'],
            'студи': 'studio',
            'апартамент': ['new_flat', 'resale_flat'],
            'дом': 'house',
            'коммерческ': 'commercial',
            'новостройк': 'new_flat',
            'вторичк': 'resale_flat'
        }

        if type_match:
            type_key = next((k for k in type_mapping.keys() if type_match.group(1).startswith(k)), None)
            if type_key:
                type_value = type_mapping[type_key]
                if isinstance(type_value, list):
                    # Для нескольких типов создаем OR условие
                    q = Q()
                    for t in type_value:
                        q |= Q(property_type__name=t)
                    q_objects &= q
                elif type_value == 'studio':
                    # Особый случай для студий - ищем по полю apartment_type
                    q_objects &= Q(apartment_type='studio')
                else:
                    q_objects &= Q(property_type__name=type_value)

        # Обработка города
        city_mapping = {
            'москв': 'Москва',
            'санкт-петербург': 'Санкт-Петербург',
            'спб': 'Санкт-Петербург',
            'екатеринбург': 'Екатеринбург',
            'новосибирск': 'Новосибирск',
            'казан': 'Казань',
            'нижн новгород': 'Нижний Новгород',
            'самар': 'Самара',
            'омск': 'Омск',
            'челябинск': 'Челябинск',
            'ростов-на-дону': 'Ростов-на-Дону',
            'уф': 'Уфа',
            'красноярск': 'Красноярск',
            'перм': 'Пермь',
            'воронеж': 'Воронеж',
            'волгоград': 'Волгоград',
            'краснодар': 'Краснодар',
            'сочи': 'Сочи'
        }

        if city_match:
            city_key = next((k for k in city_mapping.keys() if city_match.group(2).startswith(k)), None)
            if city_key:
                q_objects &= Q(location__iexact=city_mapping[city_key])

        # Обработка аренды/покупки
        if rent_match:
            q_objects &= (Q(is_rental='monthly') | Q(is_rental='daily'))
        elif buy_match:
            q_objects &= Q(is_rental='no')

        # Обработка цены
        if price_match:
            amount = float(price_match.group(3))
            unit = price_match.group(4)

            if 'млн' in unit:
                amount *= 1000000
            elif 'тыс' in unit:
                amount *= 1000

            if price_match.group(2) == 'от':
                q_objects &= Q(price__gte=amount)
            elif price_match.group(2) == 'до':
                q_objects &= Q(price__lte=amount)
            else:
                # Примерный диапазон (+-20%)
                q_objects &= Q(price__gte=amount * 0.8, price__lte=amount * 1.2)

        # Обработка площади
        if area_match:
            min_area = float(area_match.group(2))
            max_area = float(area_match.group(3)) if area_match.group(3) else min_area
            q_objects &= Q(total_area__gte=min_area, total_area__lte=max_area)

        # Универсальные фразы для поиска
        common_phrases = {
            'снять квартиру': (Q(is_rental='monthly') | Q(is_rental='daily')) &
                              (Q(property_type__name='new_flat') | Q(property_type__name='resale_flat')),
            'купить квартиру': Q(is_rental='no') &
                               (Q(property_type__name='new_flat') | Q(property_type__name='resale_flat')),
            'снять студию': (Q(is_rental='monthly') | Q(is_rental='daily')) & Q(apartment_type='studio'),
            'снять апартаменты': (Q(is_rental='monthly') | Q(is_rental='daily')) &
                                 (Q(property_type__name='new_flat') | Q(property_type__name='resale_flat')),
            'снять дом': (Q(is_rental='monthly') | Q(is_rental='daily')) & Q(property_type__name='house'),
            'купить дом': Q(is_rental='no') & Q(property_type__name='house'),
            'новостройка': Q(property_type__name='new_flat'),
            'вторичка': Q(property_type__name='resale_flat'),
            'коммерческая': Q(property_type__name='commercial')
        }

        # Проверяем полные фразы в первую очередь
        for phrase, condition in common_phrases.items():
            if phrase in value:
                q_objects &= condition
                break

        # Если не найдено конкретных фильтров, ищем по всем полям
        if not q_objects:
            terms = value.split()
            for term in terms:
                if len(term) > 2:  # Игнорируем слишком короткие термины
                    q_objects |= (
                            Q(title__icontains=term) |
                            Q(description__icontains=term) |
                            Q(location__icontains=term) |
                            Q(address__icontains=term) |
                            Q(metro_station__icontains=term) |
                            Q(property_type__name__icontains=term) |
                            Q(apartment_type__icontains=term)
                    )

        return queryset.filter(q_objects).distinct() if q_objects else queryset