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
]

# Полный словарь соответствия названий линий и их цветов
LINE_COLORS = {
    # Метрополитен
    'Сокольническая': '#FF0000',
    'Замоскворецкая': '#008000',
    'Арбатско-Покровская': '#0000FF',
    'Филёвская': '#00BFFF',
    'Кольцевая': '#A52A2A',
    'Калужско-Рижская': '#FFA500',
    'Таганско-Краснопресненская': '#800080',
    'Калининская': '#FFC0CB',
    'Серпуховско-Тимирязевская': '#808080',
    'Люблинско-Дмитровская': '#7CFC00',
    'Бутовская': '#8DD8D8',
    'Солнцевская': '#8DD8D8',
    'Некрасовская': '#FF69B4',
    'Большая кольцевая': '#8B4513',
    'Троицкая': '#00CED1',

    # МЦК
    'МЦК': '#8B4513',

    # МЦД
    'МЦД-1': '#DAA520',  # Белорусско-Савёловский
    'МЦД-2': '#FF00FF',  # Курско-Рижский
    'МЦД-3': '#FFEFD5',  # Ленинградско-Казанский
    'МЦД-4': '#98FF98',  # Калужско-Нижегородский
    'МЦД-5': '#00FF7F',  # Ярославско-Павелецкий

    # Монорельс
    'Монорельс': '#8B008B',
}

# Полный словарь всех станций московского метро с указанием линии и цвета
SPECIAL_STATIONS = {
    # Арбатско-Покровская линия (3)
    'Митино': {'line': 'Арбатско-Покровская линия', 'line_color': '#0000FF'},
    'Пятницкое шоссе': {'line': 'Арбатско-Покровская линия', 'line_color': '#0000FF'},
    'Славянский бульвар': {'line': 'Арбатско-Покровская линия', 'line_color': '#0000FF'},
    'Кунцевская': {'line': 'Арбатско-Покровская линия', 'line_color': '#0000FF'},
    'Молодёжная': {'line': 'Арбатско-Покровская линия', 'line_color': '#0000FF'},
    'Крылатское': {'line': 'Арбатско-Покровская линия', 'line_color': '#0000FF'},
    'Строгино': {'line': 'Арбатско-Покровская линия', 'line_color': '#0000FF'},
    'Мякинино': {'line': 'Арбатско-Покровская линия', 'line_color': '#0000FF'},
    'Волоколамская': {'line': 'Арбатско-Покровская линия', 'line_color': '#0000FF'},

    # Замоскворецкая линия (2)
    'Автозаводская': {'line': 'Замоскворецкая линия', 'line_color': '#008000'},
    'Аэропорт': {'line': 'Замоскворецкая линия', 'line_color': '#008000'},
    'Беломорская': {'line': 'Замоскворецкая линия', 'line_color': '#008000'},
    'Речной вокзал': {'line': 'Замоскворецкая линия', 'line_color': '#008000'},
    'Сокол': {'line': 'Замоскворецкая линия', 'line_color': '#008000'},
    'Войковская': {'line': 'Замоскворецкая линия', 'line_color': '#008000'},
    'Водный стадион': {'line': 'Замоскворецкая линия', 'line_color': '#008000'},
    'Ховрино': {'line': 'Замоскворецкая линия', 'line_color': '#008000'},

    # Калининско-Солнцевская линия (8)
    'Аэропорт Внуково': {'line': 'Калининско-Солнцевская линия', 'line_color': '#FFD700'},
    'Боровское шоссе': {'line': 'Калининско-Солнцевская линия', 'line_color': '#FFD700'},
    'Говорово': {'line': 'Калининско-Солнцевская линия', 'line_color': '#FFD700'},
    'Минская': {'line': 'Калининско-Солнцевская линия', 'line_color': '#FFD700'},
    'Новопеределкино': {'line': 'Калининско-Солнцевская линия', 'line_color': '#FFD700'},
    'Парк Победы': {'line': 'Калининско-Солнцевская линия', 'line_color': '#FFD700'},
    'Пыхтино': {'line': 'Калининско-Солнцевская линия', 'line_color': '#FFD700'},
    'Рассказовка': {'line': 'Калининско-Солнцевская линия', 'line_color': '#FFD700'},
    'Солнцево': {'line': 'Калининско-Солнцевская линия', 'line_color': '#FFD700'},

    # Калужско-Рижская линия (6)
    'Академическая': {'line': 'Калужско-Рижская линия', 'line_color': '#FFA500'},
    'Бабушкинская': {'line': 'Калужско-Рижская линия', 'line_color': '#FFA500'},
    'Ленинский проспект': {'line': 'Калужско-Рижская линия', 'line_color': '#FFA500'},
    'Медведково': {'line': 'Калужско-Рижская линия', 'line_color': '#FFA500'},
    'Тёплый Стан': {'line': 'Калужско-Рижская линия', 'line_color': '#FFA500'},

    # Люблинско-Дмитровская линия (10)
    'Верхние Лихоборы': {'line': 'Люблинско-Дмитровская линия', 'line_color': '#7CFC00'},
    'Лианозово': {'line': 'Люблинско-Дмитровская линия', 'line_color': '#7CFC00'},
    'Окружная': {'line': 'Люблинско-Дмитровская линия', 'line_color': '#7CFC00'},
    'Селигерская': {'line': 'Люблинско-Дмитровская линия', 'line_color': '#7CFC00'},
    'Физтех': {'line': 'Люблинско-Дмитровская линия', 'line_color': '#7CFC00'},
    'Яхромская': {'line': 'Люблинско-Дмитровская линия', 'line_color': '#7CFC00'},

    # Большая кольцевая линия (11)
    'Аминьевская': {'line': 'Большая кольцевая линия', 'line_color': '#8B4513'},
    'Давыдково': {'line': 'Большая кольцевая линия', 'line_color': '#8B4513'},
    'Мнёвники': {'line': 'Большая кольцевая линия', 'line_color': '#8B4513'},
    'Народное Ополчение': {'line': 'Большая кольцевая линия', 'line_color': '#8B4513'},
    'Петровский парк': {'line': 'Большая кольцевая линия', 'line_color': '#8B4513'},
    'Терехово': {'line': 'Большая кольцевая линия', 'line_color': '#8B4513'},
    'Хорошёвская': {'line': 'Большая кольцевая линия', 'line_color': '#8B4513'},
    'ЦСКА': {'line': 'Большая кольцевая линия', 'line_color': '#8B4513'},

    # Серпуховско-Тимирязевская линия (9)
    'Алтуфьево': {'line': 'Серпуховско-Тимирязевская линия', 'line_color': '#808080'},
    'Бибирево': {'line': 'Серпуховско-Тимирязевская линия', 'line_color': '#808080'},
    'Владыкино': {'line': 'Серпуховско-Тимирязевская линия', 'line_color': '#808080'},
    'Нагатинская': {'line': 'Серпуховско-Тимирязевская линия', 'line_color': '#808080'},
    'Нахимовский проспект': {'line': 'Серпуховско-Тимирязевская линия', 'line_color': '#808080'},
    'Отрадное': {'line': 'Серпуховско-Тимирязевская линия', 'line_color': '#808080'},
    'Петровско-Разумовская': {'line': 'Серпуховско-Тимирязевская линия', 'line_color': '#808080'},
    'Савеловская': {'line': 'Серпуховско-Тимирязевская линия', 'line_color': '#808080'},
    'Серпуховская': {'line': 'Серпуховско-Тимирязевская линия', 'line_color': '#808080'},
    'Тимирязевская': {'line': 'Серпуховско-Тимирязевская линия', 'line_color': '#808080'},

    # Таганско-Краснопресненская линия (7)
    'Октябрьское поле': {'line': 'Таганско-Краснопресненская линия', 'line_color': '#800080'},
    'Планерная': {'line': 'Таганско-Краснопресненская линия', 'line_color': '#800080'},
    'Полежаевская': {'line': 'Таганско-Краснопресненская линия', 'line_color': '#800080'},
    'Спартак': {'line': 'Таганско-Краснопресненская линия', 'line_color': '#800080'},
    'Сходненская': {'line': 'Таганско-Краснопресненская линия', 'line_color': '#800080'},
    'Тушинская': {'line': 'Таганско-Краснопресненская линия', 'line_color': '#800080'},
    'Щукинская': {'line': 'Таганско-Краснопресненская линия', 'line_color': '#800080'},

    # Филёвская линия (4)
    'Кутузовская': {'line': 'Филёвская линия', 'line_color': '#00BFFF'},
    'Международная': {'line': 'Филёвская линия', 'line_color': '#00BFFF'},
    'Пионерская': {'line': 'Филёвская линия', 'line_color': '#00BFFF'},
    'Фили': {'line': 'Филёвская линия', 'line_color': '#00BFFF'},
    'Багратионовская': {'line': 'Филёвская линия', 'line_color': '#00BFFF'},
    'Филевский парк': {'line': 'Филёвская линия', 'line_color': '#00BFFF'},

    # МЦК (14)
    'Балтийская': {'line': 'МЦК', 'line_color': '#8B4513'},
    'Зорге': {'line': 'МЦК', 'line_color': '#8B4513'},
    'Коптево': {'line': 'МЦК', 'line_color': '#8B4513'},
    'Лихоборы': {'line': 'МЦК', 'line_color': '#8B4513'},
    'Панфиловская': {'line': 'МЦК', 'line_color': '#8B4513'},
    'Стрешнево': {'line': 'МЦК', 'line_color': '#8B4513'},
    'Хорошёво': {'line': 'МЦК', 'line_color': '#8B4513'},
    'Шелепиха': {'line': 'МЦК', 'line_color': '#8B4513'},

    # МЦД-1 (D1)
    'Бескудниково': {'line': 'МЦД-1', 'line_color': '#DAA520'},
    'Дегунино': {'line': 'МЦД-1', 'line_color': '#DAA520'},
    'Тестовская': {'line': 'МЦД-1', 'line_color': '#DAA520'},
    'Баковка': {'line': 'МЦД-1', 'line_color': '#DAA520'},
    'Водники': {'line': 'МЦД-1', 'line_color': '#DAA520'},
    'Долгопрудная': {'line': 'МЦД-1', 'line_color': '#DAA520'},
    'Лобня': {'line': 'МЦД-1', 'line_color': '#DAA520'},
    'Марк': {'line': 'МЦД-1', 'line_color': '#DAA520'},
    'Немчиновка': {'line': 'МЦД-1', 'line_color': '#DAA520'},
    'Новодачная': {'line': 'МЦД-1', 'line_color': '#DAA520'},
    'Одинцово': {'line': 'МЦД-1', 'line_color': '#DAA520'},
    'Рабочий Посёлок': {'line': 'МЦД-1', 'line_color': '#DAA520'},
    'Сетунь': {'line': 'МЦД-1', 'line_color': '#DAA520'},
    'Сколково': {'line': 'МЦД-1', 'line_color': '#DAA520'},
    'Хлебниково': {'line': 'МЦД-1', 'line_color': '#DAA520'},
    'Шереметьевская': {'line': 'МЦД-1', 'line_color': '#DAA520'},

    # МЦД-2 (D2)
    'Аникеевка': {'line': 'МЦД-2', 'line_color': '#FF00FF'},
    'Красный Балтиец': {'line': 'МЦД-2', 'line_color': '#FF00FF'},
    'Гражданская': {'line': 'МЦД-2', 'line_color': '#FF00FF'},
    'Красногорская': {'line': 'МЦД-2', 'line_color': '#FF00FF'},
    'Нахабино': {'line': 'МЦД-2', 'line_color': '#FF00FF'},
    'Опалиха': {'line': 'МЦД-2', 'line_color': '#FF00FF'},
    'Павшино': {'line': 'МЦД-2', 'line_color': '#FF00FF'},
    'Пенягино': {'line': 'МЦД-2', 'line_color': '#FF00FF'},
    'Подольск': {'line': 'МЦД-2', 'line_color': '#FF00FF'},
    'Силикатная': {'line': 'МЦД-2', 'line_color': '#FF00FF'},
    'Трикотажная': {'line': 'МЦД-2', 'line_color': '#FF00FF'},

    # МЦД-3 (D3)
    'Грачёвская': {'line': 'МЦД-3', 'line_color': '#FFEFD5'},
    'Есенинская': {'line': 'МЦД-3', 'line_color': '#FFEFD5'},
    'Зеленоград-Крюково': {'line': 'МЦД-3', 'line_color': '#FFEFD5'},
    'Ипподром': {'line': 'МЦД-3', 'line_color': '#FFEFD5'},
    'Кратово': {'line': 'МЦД-3', 'line_color': '#FFEFD5'},
    'Левобережная': {'line': 'МЦД-3', 'line_color': '#FFEFD5'},
    'Молжаниново': {'line': 'МЦД-3', 'line_color': '#FFEFD5'},
    'Моссельмаш': {'line': 'МЦД-3', 'line_color': '#FFEFD5'},
    'Новоподрезково': {'line': 'МЦД-3', 'line_color': '#FFEFD5'},
    'Подрезково': {'line': 'МЦД-3', 'line_color': '#FFEFD5'},
    'Раменское': {'line': 'МЦД-3', 'line_color': '#FFEFD5'},
    'Сходня': {'line': 'МЦД-3', 'line_color': '#FFEFD5'},
    'Удельная': {'line': 'МЦД-3', 'line_color': '#FFEFD5'},
    'Фабричная': {'line': 'МЦД-3', 'line_color': '#FFEFD5'},
    'Фирсановская': {'line': 'МЦД-3', 'line_color': '#FFEFD5'},
    'Химки': {'line': 'МЦД-3', 'line_color': '#FFEFD5'},

    # МЦД-4 (D4)
    'Апрелевка': {'line': 'МЦД-4', 'line_color': '#98FF98'},
    'Внуково': {'line': 'МЦД-4', 'line_color': '#98FF98'},
    'Каланчёвская': {'line': 'МЦД-4', 'line_color': '#98FF98'},
    'Кокошкино': {'line': 'МЦД-4', 'line_color': '#98FF98'},
    'Крёкшино': {'line': 'МЦД-4', 'line_color': '#98FF98'},
    'Лесной Городок': {'line': 'МЦД-4', 'line_color': '#98FF98'},
    'Матвеевская': {'line': 'МЦД-4', 'line_color': '#98FF98'},
    'Мещерская': {'line': 'МЦД-4', 'line_color': '#98FF98'},
    'Мичуринец': {'line': 'МЦД-4', 'line_color': '#98FF98'},
    'Переделкино': {'line': 'МЦД-4', 'line_color': '#98FF98'},
    'Победа': {'line': 'МЦД-4', 'line_color': '#98FF98'},
    'Поклонная': {'line': 'МЦД-4', 'line_color': '#98FF98'},
    'Санино': {'line': 'МЦД-4', 'line_color': '#98FF98'},
    'Солнечная': {'line': 'МЦД-4', 'line_color': '#98FF98'},
    'Толстопальцево': {'line': 'МЦД-4', 'line_color': '#98FF98'},

    # Монорельс
    'Выставочный центр': {'line': 'Монорельс', 'line_color': '#8B008B'},
    'Телецентр': {'line': 'Монорельс', 'line_color': '#8B008B'},
    'Улица Академика Королёва': {'line': 'Монорельс', 'line_color': '#8B008B'},
    'Улица Милашенкова': {'line': 'Монорельс', 'line_color': '#8B008B'},
    'Улица Сергея Эйзенштейна': {'line': 'Монорельс', 'line_color': '#8B008B'},

    # ... (добавьте здесь остальные станции из вашего списка)
}


class Command(BaseCommand):
    help = 'Load and update metro stations from predefined data'

    def handle(self, *args, **options):
        self.stdout.write("Starting to load metro stations...", style_func=self.style.HTTP_INFO)

        # Очищаем существующие данные (опционально)
        # MetroStation.objects.all().delete()

        stats = {
            'created': 0,
            'updated': 0,
            'skipped': 0
        }

        for city in CITIES_WITH_METRO:
            self.stdout.write(f"\nProcessing city: {city}", style_func=self.style.HTTP_INFO)

            for station_name, data in SPECIAL_STATIONS.items():
                try:
                    # Создаем или обновляем станцию
                    obj, created = MetroStation.objects.update_or_create(
                        city=city,
                        name=station_name,
                        defaults={
                            'line': data['line'],
                            'line_color': data['line_color'],
                            'coordinates': Point(0, 0, srid=4326)  # Заглушка для координат
                        }
                    )

                    if created:
                        stats['created'] += 1
                        self.stdout.write(f"Created station: {station_name}", style_func=self.style.SUCCESS)
                    else:
                        stats['updated'] += 1
                        self.stdout.write(f"Updated station: {station_name}", style_func=self.style.SUCCESS)

                except Exception as e:
                    stats['skipped'] += 1
                    self.stdout.write(f"Error processing {station_name}: {str(e)}", style_func=self.style.ERROR)

        # Выводим статистику
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS(f"Created: {stats['created']} stations"))
        self.stdout.write(self.style.SUCCESS(f"Updated: {stats['updated']} stations"))
        self.stdout.write(self.style.WARNING(f"Skipped: {stats['skipped']} stations"))
        self.stdout.write("=" * 50 + "\n")
        self.stdout.write("Finished loading metro stations!", style_func=self.style.SUCCESS)