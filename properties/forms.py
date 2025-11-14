from django import forms
from django.utils import timezone
from .models import Property, PropertyImage, ListingType

from django.contrib.gis.geos import Point

class PropertyForm(forms.ModelForm):
    apartment_type = forms.ChoiceField(
        choices=[
            ('', '---------'),
            ('studio', 'Студия'),
            ('apartment', 'Апартаменты'),
        ],
        required=False,
        label='Тип квартиры'
    )

    floor = forms.IntegerField(
        required=False,
        label='Этаж',
        min_value=1,
        help_text='Номер этажа квартиры'
    )

    total_floors = forms.IntegerField(
        required=False,
        label='Всего этажей в доме',
        min_value=1,
        help_text='Общее количество этажей в доме'
    )

    rooms = forms.IntegerField(
        label='Количество комнат',
        min_value=1,
        required=True,
        help_text='Минимум 1 комната'
    )

    is_rental = forms.ChoiceField(
        choices=[
            ('no', 'Не арендное'),
            ('monthly', 'Аренда помесячно'),
            ('daily', 'Аренда посуточно'),
        ],
        required=False,
        label='Тип аренды'
    )

    monthly_price = forms.DecimalField(
        required=False,
        label='Цена за месяц (₽)',
        min_value=0,
        max_digits=12,
        decimal_places=2,
        help_text='Цена в рублях за месяц аренды'
    )

    daily_price = forms.DecimalField(
        required=False,
        label='Цена за сутки (₽)',
        min_value=0,
        max_digits=12,
        decimal_places=2,
        help_text='Цена в рублях за сутки аренды'
    )

    construction_year = forms.IntegerField(
        required=False,
        label='Год постройки',
        min_value=1800,
        max_value=timezone.now().year + 10,
        help_text='Год постройки здания'
    )

    district = forms.CharField(
        required=False,
        label='Район',
        max_length=100,
        help_text='Район города'
    )

    # Поле для карты
    map_coordinates = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

    location = forms.CharField(
        required=False,
        label='Город',
        max_length=200,
        help_text='Город, где находится объект'
    )

    address = forms.CharField(
        required=False,
        label='Адрес',
        widget=forms.Textarea(attrs={'rows': 2}),
        help_text='Полный адрес объекта'
    )
    images = forms.FileField(
        required=False,
        label='Дополнительные изображения',
        widget=forms.ClearableFileInput(),
        help_text='Максимум 10 изображений'
    )

    class Meta:
        model = Property
        fields = [
            'description', 'price', 'status', 'broker', 'developer', 'is_premium',
            'main_image', 'rooms', 'location', 'address', 'apartment_type',
            'floor', 'total_floors', 'has_finishing', 'delivery_year',
            'is_delivered', 'living_area', 'total_area', 'metro_station',
            'is_rental', 'monthly_price', 'daily_price', 'construction_year',
            'district', 'map_coordinates', 'images'  # Добавлено images
        ]
        widgets = {
            'status': forms.HiddenInput(),
            'broker': forms.HiddenInput(),
            'developer': forms.HiddenInput(),
            'is_premium': forms.HiddenInput(),
            'description': forms.Textarea(attrs={'rows': 4}),
            'has_finishing': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'is_delivered': forms.CheckboxInput(attrs={'class': 'form-checkbox'})
        }

    def __init__(self, *args, **kwargs):
        self.property_type = kwargs.pop('property_type', None)
        super().__init__(*args, **kwargs)

        self.fields['status'].initial = 'active'
        self.fields['is_premium'].initial = False

        if self.property_type and self.property_type.name in ['new_flat', 'resale_flat']:
            self.fields['floor'].required = True
        else:
            self.fields.pop('apartment_type', None)
            self.fields.pop('floor', None)

        if self.property_type and self.property_type.name == 'resale_flat':
            self.fields['is_rental'].widget.attrs.update({'class': 'rental-toggle'})
        else:
            self.fields.pop('is_rental', None)
            self.fields.pop('monthly_price', None)
            self.fields.pop('daily_price', None)
            self.fields['price'].required = True
            self.fields['price'].widget = forms.NumberInput(attrs={'class': 'form-control'})

    def clean(self):
        cleaned_data = super().clean()
        is_rental = cleaned_data.get('is_rental')
        property_type = getattr(self, 'property_type', None)

        if not property_type:
            raise forms.ValidationError("Не указан тип недвижимости")

        required_fields = {
            'rooms': 'Укажите количество комнат',
            'total_area': 'Укажите общую площадь',
        }

        for field, error_msg in required_fields.items():
            if not cleaned_data.get(field):
                self.add_error(field, error_msg)

        if property_type.name in ['new_flat', 'resale_flat']:
            if not cleaned_data.get('floor'):
                self.add_error('floor', 'Укажите этаж')

            if cleaned_data.get('floor') and cleaned_data.get('total_floors'):
                if cleaned_data['floor'] > cleaned_data['total_floors']:
                    self.add_error('floor', 'Этаж не может быть больше общего количества этажей')

        MAX_PRICE = 10 ** 9

        if is_rental == 'monthly':
            if 'monthly_price' in self.fields:
                monthly_price = cleaned_data.get('monthly_price')
                if monthly_price is None:
                    self.add_error('monthly_price', 'Укажите цену за месяц')
                elif monthly_price <= 0:
                    self.add_error('monthly_price', 'Цена за месяц должна быть больше нуля')
                elif monthly_price > MAX_PRICE:
                    self.add_error('monthly_price', 'Цена за месяц слишком высока')

                cleaned_data['price'] = 0
                cleaned_data['daily_price'] = None

        elif is_rental == 'daily':
            if 'daily_price' in self.fields:
                daily_price = cleaned_data.get('daily_price')
                if daily_price is None:
                    self.add_error('daily_price', 'Укажите цену за сутки')
                elif daily_price <= 0:
                    self.add_error('daily_price', 'Цена за сутки должна быть больше нуля')
                elif daily_price > MAX_PRICE:
                    self.add_error('daily_price', 'Цена за сутки слишком высока')

                cleaned_data['price'] = 0
                cleaned_data['monthly_price'] = None

        else:
            price = cleaned_data.get('price')
            if price is None:
                self.add_error('price', 'Укажите цену объекта')
            elif price <= 0:
                self.add_error('price', 'Цена должна быть больше нуля')
            elif price > MAX_PRICE:
                self.add_error('price', 'Цена слишком высока')

            if 'monthly_price' in self.fields:
                cleaned_data['monthly_price'] = None
            if 'daily_price' in self.fields:
                cleaned_data['daily_price'] = None

        if 'main_image' not in self.files and not self.instance.main_image:
            self.add_error('main_image', 'Главное изображение обязательно')

        if cleaned_data.get('delivery_year'):
            current_year = timezone.now().year
            if cleaned_data['delivery_year'] < 1900 or cleaned_data['delivery_year'] > current_year + 10:
                self.add_error('delivery_year', 'Некорректный год сдачи')

        if is_rental in ['monthly', 'daily'] and property_type.name != 'resale_flat':
            self.add_error('is_rental', 'Аренда доступна только для вторичного жилья')

        return cleaned_data

    def clean_main_image(self):
        image = self.cleaned_data.get('main_image')
        if not image:
            raise forms.ValidationError("Главное изображение обязательно")
        return image


class PropertyImageForm(forms.ModelForm):
    images = forms.FileField(
        label='Дополнительные фото (до 10)',
        required=False,
        widget=forms.FileInput(),
        help_text='Максимум 10 изображений'
    )

    class Meta:
        model = PropertyImage
        fields = ['images']


class ListingTypeForm(forms.Form):
    listing_type = forms.ModelChoiceField(
        queryset=ListingType.objects.all(),
        widget=forms.RadioSelect,
        empty_label=None,
        label='Выберите тип размещения'
    )

    def __init__(self, *args, **kwargs):
        # Убрать user из kwargs, если он передается
        kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['listing_type'].queryset = ListingType.objects.all()