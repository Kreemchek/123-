import os
import django

# Настройка окружения Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project_name.settings')
django.setup()

from properties.models import PropertyType

def init_property_types():
    PropertyType.objects.all().delete()

    types = [
        ('new_flat', 'Новостройка'),
        ('resale_flat', 'Вторичка'),
        ('commercial', 'Нежилое помещение'),
        ('house', 'Дом')
    ]

    for name, display in types:
        PropertyType.objects.create(name=name, description=f"Тип недвижимости: {display}")

    print("Property types initialized successfully")

if __name__ == "__main__":
    init_property_types()