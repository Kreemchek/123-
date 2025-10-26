# properties/management/commands/load_metro_stations.py
from django.core.management.base import BaseCommand
from properties.models import MetroStation
from django.contrib.gis.geos import Point
import requests
from django.conf import settings
import logging
import re
import time
from collections import defaultdict

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

# Полный словарь соответствия названий линий и их цветов
LINE_COLORS = {


    # Санкт-Петербург
    'Кировско-Выборгская': '#FF0000',
    'Московско-Петроградская': '#0000FF',
    'Невско-Василеостровская': '#008000',
    'Правобережная': '#FFA500',
    'Фрунзенско-Приморская': '#800080',
    '1': '#FF0000',
    '2': '#0000FF',
    '3': '#008000',
    '4': '#FFA500',
    '5': '#800080',


}

# Особые случаи станций
SPECIAL_STATIONS = {

    # Санкт-Петербург
    'станция Технологический институт-1': {'line': 'Кировско-Выборгская линия', 'line_color': '#FF0000'},
    'станция Технологический институт-2': {'line': 'Московско-Петроградская линия', 'line_color': '#0000FF'},
    'станция Площадь Александра Невского-1': {'line': 'Невско-Василеостровская линия', 'line_color': '#008000'},
    'станция Площадь Александра Невского-2': {'line': 'Правобережная линия', 'line_color': '#FFA500'},
    'станция Спасская': {'line': 'Правобережная линия', 'line_color': '#FFA500'},
    'станция Адмиралтейская': {'line': 'Фрунзенско-Приморская линия', 'line_color': '#800080'},
}

# Нормализация названий станций
STATION_NAME_MAPPING = {
    # Москва
    'Улица Подбельского': 'Бульвар Рокоссовского',
    'Кировская': 'Чистые пруды',
    'Мясницкая': 'Чистые пруды',
    'Дзержинская': 'Лубянка',
    'Охотный ряд': 'Охотный Ряд',
    'Станция имени Л. М. Кагановича': 'Охотный Ряд',
    'Проспект Маркса': 'Охотный Ряд',
    'Дворец Советов': 'Кропоткинская',
    'Парк культуры имени Горького': 'Парк культуры',
    'Ленинские горы': 'Воробьёвы горы',
    'Ленино': 'Царицыно',
    'Завод имени Сталина': 'Автозаводская',
    'Завод имени Лихачева': 'Автозаводская',
    'Площадь Свердлова': 'Театральная',
    'Горьковская': 'Тверская',
    'Арбатская площадь': 'Арбатская',
    'Спартаковская': 'Бауманская',
    'Сталинская': 'Семеновская',
    'Стадион народов': 'Партизанская',
    'Измайловская': 'Партизанская',
    'Измайловский парк': 'Партизанская',
    'Стадион им. Сталина': 'Партизанская',
    'Улица Коминтерна': 'Александровский сад',
    'Им. Коминтерна': 'Александровский сад',
    'Калининская': 'Александровский сад',
    'Воздвиженка': 'Александровский сад',
    'Деловой центр': 'Выставочная',
    'Ботанический сад': 'Проспект Мира',
    'Калужская': 'Октябрьская',
    'Серпуховская': 'Добрынинская',
    'ВСХВ': 'ВДНХ',
    'Мир': 'Алексеевская',
    'Щербаковская': 'Алексеевская',
    'Ново-Алексеевская': 'Алексеевская',
    'Колхозная': 'Сухаревская',
    'Площадь Ногина': 'Китай-город',
    'Ждановская': 'Выхино',
    'Битцевский парк': 'Новоясеневская',

    # Станции с приставкой "станция"
    'станция Беговая': 'Беговая',
    'станция Марьина Роща': 'Марьина Роща',
    'станция Курская': 'Курская',
    'станция Савёловская': 'Савёловская',
    'станция Лужники': 'Лужники',
    'станция Рижская': 'Рижская',
    'станция Белорусская': 'Белорусская',
    'станция Серп и Молот': 'Серп и Молот',
    'станция Митьково': 'Митьково',
    'станция Нижегородская': 'Нижегородская',
    'станция Лефортово': 'Лефортово',
}

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
        self.cleanup_and_normalize_stations()

        stats = defaultdict(int)
        missing_data = {
            'line': [],
            'color': []
        }

        for city in CITIES_WITH_METRO:
            self.stdout.write(f"\nProcessing city: {city}")
            try:
                # Получаем координаты города
                city_url = f"https://geocode-maps.yandex.ru/1.x/?apikey={settings.YANDEX_GEOCODER_API_KEY}&format=json&geocode={city}"
                city_response = requests.get(city_url)
                city_response.raise_for_status()
                city_data = city_response.json()

                # Извлекаем координаты города
                city_pos = city_data['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos']
                lon, lat = map(float, city_pos.split())

                # Ищем метро с увеличенным радиусом
                metro_url = f"https://geocode-maps.yandex.ru/1.x/?apikey={settings.YANDEX_GEOCODER_API_KEY}&format=json&geocode={lon},{lat}&kind=metro&results=1000&spn=1.5,1.5"
                metro_response = requests.get(metro_url)
                metro_response.raise_for_status()
                metro_data = metro_response.json()

                features = metro_data.get('response', {}).get('GeoObjectCollection', {}).get('featureMember', [])
                if not features:
                    self.stdout.write(self.style.WARNING(f"No metro stations found for {city}"))
                    continue

                processed_stations = set()

                for feature in features:
                    geo_object = feature.get('GeoObject', {})
                    station_name = geo_object.get('name', '')
                    pos = geo_object.get('Point', {}).get('pos', '')
                    description = geo_object.get('description', '')

                    if not station_name or not pos:
                        continue

                    if self.is_non_metro_station(station_name):
                        continue

                    # Очистка и нормализация названия
                    original_name = station_name
                    station_name = re.sub(r'станция метро|метро', '', station_name, flags=re.IGNORECASE).strip()
                    station_name = STATION_NAME_MAPPING.get(station_name, station_name)

                    # Проверка дубликатов
                    station_key = f"{city}:{station_name}"
                    if station_key in processed_stations:
                        continue
                    processed_stations.add(station_key)

                    # Определение линии и цвета
                    line_name, line_color = self.get_line_info(original_name, description)

                    if not line_name:
                        stats['no_line'] += 1
                        missing_data['line'].append(f"{city}: {station_name}")
                        logger.warning(f"No line info for station: {station_name} (description: {description})")

                    if not line_color:
                        stats['no_color'] += 1
                        missing_data['color'].append(f"{city}: {station_name} (line: {line_name})")

                    # Сохранение станции
                    lon, lat = map(float, pos.split())
                    obj, created = MetroStation.objects.update_or_create(
                        city=city,
                        name=station_name,
                        defaults={
                            'line': line_name,
                            'line_color': line_color,
                            'coordinates': Point(lon, lat, srid=4326)
                        }
                    )

                    action = "Added" if created else "Updated"
                    self.stdout.write(f"{action} station: {station_name} (line: {line_name}, color: {line_color})")
                    stats['processed'] += 1
                    time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error loading metro stations for {city}: {str(e)}")
                self.stdout.write(self.style.ERROR(f"Error processing {city}: {str(e)}"))

        # Вывод статистики
        self.print_stats(stats, missing_data)

    def get_line_info(self, original_name, description):
        """Получает информацию о линии и цвете для станции"""
        if original_name in SPECIAL_STATIONS:
            return SPECIAL_STATIONS[original_name]['line'], SPECIAL_STATIONS[original_name]['line_color']

        if description:
            line_match = re.search(r'(\w+ линия|\d+ линия|МЦК|МЦД-\d+)', description)
            if line_match:
                line_name = line_match.group(1)
                line_key = line_name.replace(' линия', '').strip()

                # Обработка числовых линий (СПб)
                if line_key.isdigit():
                    line_number = int(line_key)
                    line_key = {
                        1: 'Кировско-Выборгская',
                        2: 'Московско-Петроградская',
                        3: 'Невско-Василеостровская',
                        4: 'Правобережная',
                        5: 'Фрунзенско-Приморская',
                    }.get(line_number, line_key)
                    line_name = f"{line_key} линия"

                # Поиск альтернативных названий
                if line_key not in LINE_COLORS:
                    for key in LINE_COLORS:
                        if key in line_key or line_key in key:
                            line_key = key
                            break

                return line_name, LINE_COLORS.get(line_key)

        return None, None

    def cleanup_and_normalize_stations(self):
        """Нормализация названий и удаление нестандартных станций"""
        normalized = deleted = 0

        for old_name, new_name in STATION_NAME_MAPPING.items():
            stations = MetroStation.objects.filter(name=old_name)
            for station in stations:
                existing = MetroStation.objects.filter(city=station.city, name=new_name).first()
                if existing:
                    existing.line = station.line or existing.line
                    existing.line_color = station.line_color or existing.line_color
                    existing.coordinates = station.coordinates or existing.coordinates
                    existing.save()
                    station.delete()
                    deleted += 1
                else:
                    station.name = new_name
                    station.save()
                    normalized += 1

        # Удаление нестандартных станций
        for station in MetroStation.objects.all():
            if self.is_non_metro_station(station.name):
                station.delete()
                deleted += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nNormalized {normalized} names, deleted {deleted} non-standard stations"
        ))

    def print_stats(self, stats, missing_data):
        """Выводит итоговую статистику"""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS(f"Processed {stats['processed']} stations"))
        self.stdout.write(self.style.WARNING(f"Stations without line info: {stats['no_line']}"))
        self.stdout.write(self.style.WARNING(f"Stations without color info: {stats['no_color']}"))

        if missing_data['line']:
            self.stdout.write("\nStations missing line information:")
            for station in missing_data['line'][:20]:  # Ограничиваем вывод
                self.stdout.write(f" - {station}")
            if len(missing_data['line']) > 20:
                self.stdout.write(f" ... and {len(missing_data['line']) - 20} more")

        if missing_data['color']:
            self.stdout.write("\nStations missing color information:")
            for station in missing_data['color'][:20]:
                self.stdout.write(f" - {station}")
            if len(missing_data['color']) > 20:
                self.stdout.write(f" ... and {len(missing_data['color']) - 20} more")

        self.stdout.write("=" * 50 + "\n")

    def is_non_metro_station(self, name):
        """Проверяет, является ли название станцией метро"""
        name_lower = name.lower()
        return any(keyword.lower() in name_lower for keyword in NON_METRO_KEYWORDS)