# properties/management/commands/load_metro_stations.py
from django.core.management.base import BaseCommand
from properties.models import MetroStation
from django.contrib.gis.geos import Point
import requests
from django.conf import settings
import logging
import re
import time

logger = logging.getLogger(__name__)

CITIES_WITH_METRO = [
    'Москва',
    'Санкт-Петербург',
    'Нижний Новгород',
    'Новосибирск',
    'Самара',
    'Екатеринбург',
    'Казань'
]

# Расширенный словарь соответствия названий линий и их цветов
LINE_COLORS = {
    # Москва
    'Сокольническая': '#FF0000',  # Красная
    'Замоскворецкая': '#008000',  # Зеленая
    'Арбатско-Покровская': '#0000FF',  # Синяя
    'Покровская': '#0000FF',  # Альтернативное название для Арбатско-Покровской
    'Филёвская': '#00BFFF',  # Голубая
    'Кольцевая': '#A52A2A',  # Коричневая
    'кольцевая': '#A52A2A',  # Строчная версия
    'Калужско-Рижская': '#FFA500',  # Оранжевая
    'Рижская': '#FFA500',  # Альтернативное название для Калужско-Рижской
    'Таганско-Краснопресненская': '#800080',  # Фиолетовая
    'Краснопресненская': '#800080',  # Альтернативное название
    'Калининская': '#FFC0CB',  # Розовая
    'Серпуховско-Тимирязевская': '#808080',  # Серая
    'Тимирязевская': '#808080',  # Альтернативное название
    'Люблинско-Дмитровская': '#7CFC00',  # Салатовая
    'Дмитровская': '#7CFC00',  # Альтернативное название
    'Бутовская': '#40E0D0',  # Бирюзовая
    'Солнцевская': '#40E0D0',  # Бирюзовая (для Солнцевской линии)
    'Некрасовская': '#FF69B4',  # Розовая (для Некрасовской линии)
    'Московское центральное кольцо': '#8B4513',  # Коричневая (для МЦК)
    'МЦК': '#8B4513',  # Сокращение для МЦК
    'Московская монорельсовая': '#6A5ACD',  # Сланцевая (для монорельса)
    'Монорельс': '#6A5ACD',  # Сокращение для монорельса

    # Санкт-Петербург
    'Кировско-Выборгская': '#FF0000',  # Красная
    'Московско-Петроградская': '#0000FF',  # Синяя
    'Невско-Василеостровская': '#008000',  # Зеленая
    'Правобережная': '#FFA500',  # Оранжевая
    'Фрунзенско-Приморская': '#800080',  # Фиолетовая
    '1': '#FF0000',  # Для линий, указанных как "1 линия"
    '2': '#0000FF',
    '3': '#008000',
    '4': '#FFA500',
    '5': '#800080',

    # Нижний Новгород
    'Автозаводская': '#FF0000',  # Красная
    'Сормовская': '#0000FF',  # Синяя
    'Мещерская': '#008000',  # Зеленая',

    # Новосибирск
    'Ленинская': '#FF0000',  # Красная
    'Дзержинская': '#0000FF',  # Синяя,

    # Самара
    'Первая': '#FF0000',  # Красная,

    # Екатеринбург
    'Первая': '#FF0000',  # Красная,

    # Казань
    'Центральная': '#FF0000',  # Красная,
}


# Словарь для обработки особых случаев станций
SPECIAL_STATIONS = {
    'станция Курская': {'line': 'Арбатско-Покровская линия', 'line_color': '#0000FF'},
    'станция Площадь трёх вокзалов (Каланчёвская)': {'line': 'Кольцевая линия', 'line_color': '#A52A2A'},
    'станция МЦД Казанский вокзал': {'line': 'МЦК', 'line_color': '#8B4513'},
    'станция Белорусская': {'line': 'Кольцевая линия', 'line_color': '#A52A2A'},
    'станция МЦД Ленинградский вокзал': {'line': 'МЦК', 'line_color': '#8B4513'},
    'станция Серп и Молот': {'line': 'МЦК', 'line_color': '#8B4513'},
    'станция Рижская': {'line': 'Калужско-Рижская линия', 'line_color': '#FFA500'},
    'станция Москва-Товарная': {'line': 'МЦК', 'line_color': '#8B4513'},
    'станция Савёловская': {'line': 'Серпуховско-Тимирязевская линия', 'line_color': '#808080'},
    'станция Митьково': {'line': 'Люблинско-Дмитровская линия', 'line_color': '#7CFC00'},
    'станция Марьина Роща': {'line': 'Люблинско-Дмитровская линия', 'line_color': '#7CFC00'},
    'станция Беговая': {'line': 'Таганско-Краснопресненская линия', 'line_color': '#800080'},
    'станция Лужники': {'line': 'Сокольническая линия', 'line_color': '#FF0000'},
}

# Список ключевых слов, которые указывают на то, что это не станция метро
NON_METRO_KEYWORDS = [
    'аэропорт', 'аэродром', 'вокзал', 'трасса', 'шоссе', 'автодорога',
    'дорога', 'километр', 'территория', 'улица', 'посёлок', 'поселок',
    'село', 'деревня', 'квартал', 'корпус', 'здание', 'терминал',
    'СНТ', 'СДТ', 'ЖК', 'Женерал', 'Эвбанк', 'Триштау', 'Эштрейту',
    'Дендропарк', 'Гора', 'река', 'речной', 'М-', 'Р-', 'К-', 'А-'
]


class Command(BaseCommand):
    help = 'Load and update metro stations from Yandex API with line information'

    def handle(self, *args, **options):
        # First, clean up non-metro stations from the database
        self.cleanup_non_metro_stations()

        total_stations_without_line = 0
        total_stations_without_color = 0
        stations_missing_line = []
        stations_missing_color = []

        for city in CITIES_WITH_METRO:
            self.stdout.write(f"\nProcessing city: {city}")
            city_stations_without_line = 0
            city_stations_without_color = 0

            try:
                # Получаем координаты города
                city_url = f"https://geocode-maps.yandex.ru/1.x/?apikey={settings.YANDEX_GEOCODER_API_KEY}&format=json&geocode={city}"
                city_response = requests.get(city_url)
                city_response.raise_for_status()
                city_data = city_response.json()

                # Извлекаем координаты города
                city_pos = city_data['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos']
                lon, lat = map(float, city_pos.split())

                # Ищем метро в радиусе 20 км от центра города
                metro_url = f"https://geocode-maps.yandex.ru/1.x/?apikey={settings.YANDEX_GEOCODER_API_KEY}&format=json&geocode={lon},{lat}&kind=metro&results=100&spn=0.3,0.3"
                metro_response = requests.get(metro_url)
                metro_response.raise_for_status()
                metro_data = metro_response.json()

                features = metro_data.get('response', {}).get('GeoObjectCollection', {}).get('featureMember', [])
                if not features:
                    self.stdout.write(self.style.WARNING(f"No metro stations found for {city}"))
                    continue

                stations_updated = 0
                processed_stations = set()  # Для отслеживания уже обработанных станций

                for feature in features:
                    geo_object = feature.get('GeoObject', {})
                    station_name = geo_object.get('name', '')
                    pos = geo_object.get('Point', {}).get('pos', '')
                    description = geo_object.get('description', '')

                    if not station_name or not pos:
                        continue

                    # Skip if this is clearly not a metro station
                    if self.is_non_metro_station(station_name):
                        continue

                    # Очищаем название от лишних слов
                    original_name = station_name
                    station_name = re.sub(r'станция метро', '', station_name, flags=re.IGNORECASE).strip()
                    station_name = re.sub(r'метро', '', station_name, flags=re.IGNORECASE).strip()

                    # Пропускаем дубликаты
                    station_key = f"{city}:{station_name}"
                    if station_key in processed_stations:
                        continue
                    processed_stations.add(station_key)

                    # Проверяем особые случаи станций
                    line_name = None
                    line_color = None
                    missing_line = False
                    missing_color = False

                    # Обработка особых случаев
                    if original_name in SPECIAL_STATIONS:
                        line_name = SPECIAL_STATIONS[original_name]['line']
                        line_color = SPECIAL_STATIONS[original_name]['line_color']
                    else:
                        # Стандартная обработка
                        if description:
                            # Ищем название линии (например, "Сокольническая линия")
                            line_match = re.search(r'(\w+ линия|\d+ линия)', description)
                            if line_match:
                                line_name = line_match.group(1)
                                line_key = line_name.replace(' линия', '').strip()

                                # Проверяем альтернативные названия линий
                                if line_key not in LINE_COLORS:
                                    # Пробуем найти альтернативное название
                                    for key in LINE_COLORS:
                                        if key in line_key or line_key in key:
                                            line_key = key
                                            break

                                line_color = LINE_COLORS.get(line_key)

                                if not line_color:
                                    city_stations_without_color += 1
                                    missing_color = True
                                    stations_missing_color.append(f"{city}: {station_name} (line: {line_name})")
                            else:
                                city_stations_without_line += 1
                                missing_line = True
                                stations_missing_line.append(f"{city}: {station_name}")

                    lon, lat = map(float, pos.split())

                    # Обновляем или создаем запись
                    obj, created = MetroStation.objects.update_or_create(
                        city=city,
                        name=station_name,
                        defaults={
                            'line': line_name,
                            'line_color': line_color,
                            'coordinates': Point(lon, lat, srid=4326)
                        }
                    )

                    action = "Added NEW" if created else "Updated EXISTING"
                    self.stdout.write(f"{action} station: {station_name} (line: {line_name}, color: {line_color})")

                    stations_updated += 1
                    time.sleep(0.1)

                total_stations_without_line += city_stations_without_line
                total_stations_without_color += city_stations_without_color

                self.stdout.write(self.style.SUCCESS(f"\nProcessed {stations_updated} stations for {city}"))
                self.stdout.write(self.style.WARNING(f"Stations without line info: {city_stations_without_line}"))
                self.stdout.write(self.style.WARNING(f"Stations without color info: {city_stations_without_color}"))

            except Exception as e:
                logger.error(f"Error loading metro stations for {city}: {str(e)}")
                self.stdout.write(self.style.ERROR(f"Error processing {city}: {str(e)}"))

        # Выводим итоговую статистику
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.WARNING(f"TOTAL STATIONS WITHOUT LINE INFO: {total_stations_without_line}"))
        if stations_missing_line:
            self.stdout.write("\nStations missing line information:")
            for station in stations_missing_line:
                self.stdout.write(f" - {station}")

        self.stdout.write(
            "\n" + self.style.WARNING(f"TOTAL STATIONS WITHOUT COLOR INFO: {total_stations_without_color}"))
        if stations_missing_color:
            self.stdout.write("\nStations missing color information:")
            for station in stations_missing_color:
                self.stdout.write(f" - {station}")

        self.stdout.write("=" * 50)

    def cleanup_non_metro_stations(self):
        """Remove entries that are clearly not metro stations from the database."""
        deleted_count = 0
        for station in MetroStation.objects.all():
            if self.is_non_metro_station(station.name):
                station.delete()
                deleted_count += 1
                self.stdout.write(f"Deleted non-metro station: {station.name}")

        self.stdout.write(self.style.SUCCESS(f"\nDeleted {deleted_count} non-metro stations from database"))

    def is_non_metro_station(self, name):
        """Check if the given name is clearly not a metro station."""
        name_lower = name.lower()
        for keyword in NON_METRO_KEYWORDS:
            if keyword.lower() in name_lower:
                return True
        return False