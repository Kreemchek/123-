# properties/management/commands/load_city_centers.py

from django.core.management.base import BaseCommand
from properties.models import CityCenter
from django.contrib.gis.geos import Point
import requests
from django.conf import settings
import json


class Command(BaseCommand):
    help = 'Load city centers from Yandex Geocoder'

    def handle(self, *args, **options):
        cities = ['Москва', 'Санкт-Петербург', 'Новосибирск', 'Екатеринбург', 'Казань']

        for city in cities:
            if not CityCenter.objects.filter(city=city).exists():
                try:
                    url = f"https://geocode-maps.yandex.ru/1.x/?apikey={settings.YANDEX_GEOCODER_API_KEY}&format=json&geocode={city}&kind=locality"
                    response = requests.get(url)
                    response.raise_for_status()  # Проверяем на ошибки HTTP
                    data = response.json()

                    # Добавим проверку структуры ответа
                    if not data.get('response', {}).get('GeoObjectCollection', {}).get('featureMember'):
                        self.stdout.write(self.style.WARNING(f'No features found for {city}'))
                        continue

                    feature = data['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']
                    pos = feature['Point']['pos']
                    lon, lat = map(float, pos.split())

                    CityCenter.objects.create(
                        city=city,
                        coordinates=Point(lon, lat, srid=4326)
                    )
                    self.stdout.write(self.style.SUCCESS(f'Added center for {city}'))

                except requests.exceptions.RequestException as e:
                    self.stdout.write(self.style.ERROR(f'HTTP error for {city}: {str(e)}'))
                except (KeyError, IndexError, ValueError) as e:
                    self.stdout.write(self.style.ERROR(f'Data parsing error for {city}: {str(e)}'))
                    self.stdout.write(self.style.WARNING(f'Response: {json.dumps(data, indent=2, ensure_ascii=False)}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Unexpected error for {city}: {str(e)}'))