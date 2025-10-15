# Стандартные Django импорты
from datetime import timedelta
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, ExpressionWrapper, F, FloatField
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.conf import settings
# Гео-импорты
from django.contrib.gis.measure import Distance, D
from django.contrib.gis.geos import Point
import json
# Сторонние библиотеки
from django_filters.views import FilterView
import uuid
import requests
from django.http import JsonResponse
from django.views import View
# Локальные импорты
from brokers.models import BrokerProfile
from .models import Property, PropertyImage, PropertyType, ListingType, MetroStation
from .filters import PropertyFilter
from .forms import PropertyForm, ListingTypeForm
from accounts.models import User, ContactRequest, Favorite
from payments.models import Payment
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib.gis.geos import Point
import logging
from django.core.serializers.json import DjangoJSONEncoder
logger = logging.getLogger(__name__)


# properties/views.py
class PropertyListView(FilterView):
    model = Property
    template_name = 'properties/property_list.html'
    context_object_name = 'properties'
    filterset_class = PropertyFilter
    paginate_by = 12

    def get_queryset(self):
        # ВРЕМЕННО: показываем ВСЕ одобренные активные объекты для всех
        queryset = Property.objects.filter(
            is_approved=True,
            status='active'
        )

        # Аннотируем цену за квадратный метр
        queryset = queryset.annotate(
            price_per_sqm=ExpressionWrapper(
                F('price') / F('total_area'),
                output_field=FloatField()
            )
        )

        # Обработка поискового запроса
        search_query = self.request.GET.get('search')
        if search_query:
            # Используем фильтр для универсального поиска
            return PropertyFilter(data={'search': search_query}, queryset=queryset).qs

        # Обработка геолокации
        geo_coords = self.request.GET.get('radius_filter')
        if geo_coords:
            try:
                lat, lon, radius = map(float, geo_coords.split(','))
                center = Point(lon, lat, srid=4326)
                queryset = queryset.filter(
                    coordinates__distance_lte=(center, D(km=radius)))
            except (ValueError, IndexError):
                pass

        # Применяем все остальные фильтры
        return PropertyFilter(data=self.request.GET, queryset=queryset).qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['YANDEX_MAPS_API_KEY'] = settings.YANDEX_MAPS_API_KEY
        context['property_types'] = PropertyType.objects.all()
        context['selected_property_types'] = self.request.GET.getlist('property_type', [])
        context['selected_rental_types'] = self.request.GET.getlist('rental_type', [])

        # Получаем выбранный город из GET-параметров
        selected_city = self.request.GET.get('location', '')
        context['location'] = selected_city

        # Получаем станции метро для выбранного города
        metro_stations = MetroStation.objects.all()
        if selected_city:
            metro_stations = metro_stations.filter(city__iexact=selected_city)

        # Группируем станции по линиям
        metro_lines = []
        if selected_city:
            lines = metro_stations.exclude(line__isnull=True).exclude(line='').values_list('line', flat=True).distinct()
            for line in lines:
                stations = metro_stations.filter(line=line).order_by('name')
                if stations.exists():
                    metro_lines.append({
                        'line': line,
                        'line_color': stations.first().line_color,
                        'stations': stations
                    })

            # Добавляем станции без линии в отдельную группу
            no_line_stations = metro_stations.filter(Q(line__isnull=True) | Q(line=''))
            if no_line_stations.exists():
                metro_lines.append({
                    'line': None,
                    'line_color': '#cccccc',
                    'stations': no_line_stations
                })

        context['metro_lines'] = metro_lines

        broker_id = self.request.GET.get('broker')
        if broker_id:
            context['current_broker'] = get_object_or_404(BrokerProfile, id=broker_id)

        # Добавляем информацию о типе пользователя
        if self.request.user.is_authenticated:
            context['is_broker'] = self.request.user.is_broker
            context['is_developer'] = self.request.user.is_developer
            context['is_client'] = not (self.request.user.is_broker or self.request.user.is_developer)
        return context

    def render_to_response(self, context, **response_kwargs):
        # Обработка AJAX-запросов (например, для автодополнения)
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            properties = self.get_queryset()
            data = {
                'options': ''.join([f'<option value="{p.id}">{p.title}</option>' for p in properties])
            }
            return JsonResponse(data)
        return super().render_to_response(context, **response_kwargs)


class PropertyDetailView(DetailView):
    model = Property
    template_name = 'properties/property_detail.html'
    context_object_name = 'property'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        property = self.object

        # Логирование базовой информации
        logger.debug("=" * 50)
        logger.debug(f"PropertyDetailView: начал обработку для property_id={property.id}")
        logger.debug(f"Пользователь: {self.request.user} (аутентифицирован: {self.request.user.is_authenticated})")

        # Добавляем логирование координат
        logger.debug(f"Координаты объекта {property.id}: {property.coordinates}")
        if property.coordinates:
            try:
                logger.debug(f"Координаты (x, y): {property.coordinates.x}, {property.coordinates.y}")
                logger.debug(f"SRID: {property.coordinates.srid}")
            except Exception as e:
                logger.error(f"Ошибка при чтении координат: {str(e)}")

        # Основные данные контекста
        context['images'] = property.images.all()
        context['YANDEX_MAPS_API_KEY'] = settings.YANDEX_MAPS_API_KEY
        logger.debug(f"Yandex Maps API Key: {settings.YANDEX_MAPS_API_KEY}")

        # Проверки прав пользователя
        context['is_current_broker'] = (
                self.request.user.is_authenticated and
                self.request.user == property.broker.user
        )
        context['is_admin'] = self.request.user.is_authenticated and self.request.user.is_admin
        logger.debug(f"is_current_broker: {context['is_current_broker']}")
        logger.debug(f"is_admin: {context['is_admin']}")

        # Координаты объекта
        if property.coordinates:
            try:
                context['coordinates_json'] = json.dumps({
                    'x': float(property.coordinates.x),
                    'y': float(property.coordinates.y)
                }, cls=DjangoJSONEncoder)
                logger.debug(f"Сформирован coordinates_json: {context['coordinates_json']}")
            except Exception as e:
                logger.error(f"Ошибка сериализации координат: {e}")
                context['coordinates_json'] = None
                logger.debug("Не удалось сериализовать координаты")
        else:
            context['coordinates_json'] = None
            logger.debug("У объекта нет координат")

        # Координаты метро
        if property.metro_coordinates:
            try:
                context['metro_coordinates_json'] = json.dumps({
                    'x': float(property.metro_coordinates.x),
                    'y': float(property.metro_coordinates.y)
                }, cls=DjangoJSONEncoder)
                logger.debug(f"Сформирован metro_coordinates_json: {context['metro_coordinates_json']}")
            except Exception as e:
                logger.error(f"Ошибка сериализации координат метро: {e}")
                context['metro_coordinates_json'] = None
        else:
            context['metro_coordinates_json'] = None
            logger.debug("У объекта нет координат метро")

        # Дополнительные проверки
        context['has_coordinates'] = bool(property.coordinates)
        context['is_client'] = (
                self.request.user.is_authenticated and
                not (self.request.user.is_broker or self.request.user.is_developer or self.request.user.is_admin)
        )
        logger.debug(f"has_coordinates: {context['has_coordinates']}")
        logger.debug(f"is_client: {context['is_client']}")

        # Проверка избранного
        if self.request.user.is_authenticated:
            context['is_favorite'] = Favorite.objects.filter(
                user=self.request.user,
                property=property
            ).exists()
            logger.debug(f"is_favorite: {context['is_favorite']}")

            context['contact_paid'] = Payment.objects.filter(
                user=self.request.user,
                description__contains=f"Контакт с брокером {property.broker.id} по объекту {property.id}",
                status='completed'
            ).exists()
            logger.debug(f"contact_paid: {context['contact_paid']}")

            context['existing_request'] = ContactRequest.objects.filter(
                requester=self.request.user,
                broker=property.broker.user,
                property=property
            ).first()
            logger.debug(f"existing_request: {context['existing_request']}")

            context['is_broker'] = self.request.user.user_type == User.UserType.BROKER
            logger.debug(f"is_broker: {context['is_broker']}")

        # Логирование завершения
        logger.debug("=" * 50)
        logger.debug("PropertyDetailView: завершил обработку")
        logger.debug(f"Ключи контекста: {list(context.keys())}")

        return context


class PropertyCreateView(LoginRequiredMixin, CreateView):
    model = Property
    form_class = PropertyForm
    template_name = 'properties/property_create_form.html'
    success_url = reverse_lazy('dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['YANDEX_MAPS_API_KEY'] = settings.YANDEX_MAPS_API_KEY

        context['YANDEX_GEO_SUGGEST_API_KEY'] = settings.YANDEX_GEO_SUGGEST_API_KEY
        context['max_images'] = 10
        context['property_type'] = get_object_or_404(PropertyType, name=self.kwargs['property_type'])
        context['property_type_name'] = context['property_type'].get_name_display()
        context['show_apartment_fields'] = context['property_type'].name in ['new_flat', 'resale_flat']
        context['step'] = 1
        return context

    def form_valid(self, form):
        with transaction.atomic():
            listing_type_id = self.request.session.get('selected_listing_type')
            if not listing_type_id:
                form.add_error(None, "Тип размещения не выбран")
                return self.form_invalid(form)

            listing_type = ListingType.objects.get(id=listing_type_id)

            if self.request.user.balance < listing_type.price:
                form.add_error(None, "Недостаточно средств на балансе")
                return self.form_invalid(form)

            transaction_id = f"property_{uuid.uuid4()}"

            payment = Payment.objects.create(
                user=self.request.user,
                amount=listing_type.price,
                payment_method='balance',
                status='completed',
                description=f"Оплата размещения типа: {listing_type.name}",
                transaction_id=transaction_id
            )

            self.request.user.balance -= listing_type.price
            self.request.user.save()

            self.object = form.save(commit=False)
            self.object.property_type = get_object_or_404(
                PropertyType,
                name=self.kwargs['property_type']
            )
            self.object.broker = self.request.user.broker_profile
            self.object.is_approved = False
            self.object.creator = self.request.user
            self.object.listing_type = listing_type
            self.object.listing_end_date = timezone.now() + timedelta(days=listing_type.duration_days)
            self.object.is_featured = listing_type.is_featured

            if not hasattr(self.request.user, 'broker_profile'):
                form.add_error(None, "Профиль брокера не найден. Заполните данные в разделе профиля.")
                return self.form_invalid(form)

            if 'main_image' not in self.request.FILES:
                form.add_error('main_image', 'Главное изображение обязательно')
                return self.form_invalid(form)

            # Установка временных значений для location и address
            self.object.location = "Не указано"
            self.object.address = "Адрес будет указан позже"

            self.object.save()

            # Обработка изображений
            images = self.request.FILES.getlist('images')
            if len(images) > 10:
                form.add_error(None, "Максимальное количество изображений - 10")
                return self.form_invalid(form)

            main_image = self.request.FILES['main_image']
            PropertyImage.objects.create(
                property=self.object,
                image=main_image,
                is_main=True
            )

            for idx, img in enumerate(images[:9], start=1):
                PropertyImage.objects.create(
                    property=self.object,
                    image=img,
                    order=idx
                )

            messages.success(
                self.request,
                f"Объект успешно создан! С вашего баланса будет списано {listing_type.price} после заполнения точного адреса ₽. "
            )

            if 'selected_listing_type' in self.request.session:
                del self.request.session['selected_listing_type']

            return redirect('properties:property-detail', pk=self.object.pk)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['property_type'] = get_object_or_404(
            PropertyType,
            name=self.kwargs['property_type']
        )
        return kwargs

    def form_invalid(self, form):
        return self.render_to_response(
            self.get_context_data(form=form, images_error=form.errors)
        )


class PropertyUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Property
    form_class = PropertyForm
    template_name = 'properties/property_create_form.html'

    def test_func(self):
        obj = self.get_object()
        # Проверяем, является ли пользователь брокером-владельцем объекта
        is_broker_owner = (
                obj.broker and
                self.request.user == obj.broker.user
        )
        # ИЛИ является ли пользователь застройщиком-владельцем
        is_developer_owner = (
                obj.developer and
                self.request.user == obj.developer
        )
        return is_broker_owner or is_developer_owner

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['property_type'] = self.object.property_type
        context['property_type_name'] = self.object.property_type.get_name_display()
        context['show_apartment_fields'] = self.object.property_type.name in ['new_flat', 'resale_flat']
        context['step'] = 1
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['property_type'] = self.object.property_type
        return kwargs

    def form_valid(self, form):
        self.object = form.save()

        # Обработка новых изображений
        images = self.request.FILES.getlist('images')
        if len(images) + self.object.images.count() > 10:
            form.add_error(None, "Максимальное количество фото - 10")
            return self.form_invalid(form)

        for img in images:
            PropertyImage.objects.create(
                property=self.object,
                image=img
            )

        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('property-detail', kwargs={'pk': self.object.pk})


@login_required
def toggle_favorite(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=403)

    property = get_object_or_404(Property, pk=pk)
    favorite, created = Favorite.objects.get_or_create(
        user=request.user,
        property=property
    )

    if not created:
        favorite.delete()
        return JsonResponse({'status': 'removed', 'is_favorite': False})
    return JsonResponse({'status': 'added', 'is_favorite': True})


class BrokerFavoriteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        property = get_object_or_404(Property, pk=pk)
        Favorite.objects.get_or_create(
            user=request.user,
            property=property,
            is_broker_favorite=True
        )
        return JsonResponse({'status': 'added'})


class PropertyDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Property
    success_url = reverse_lazy('dashboard')

    def test_func(self):
        obj = self.get_object()
        # Проверяем, является ли пользователь брокером-владельцем объекта
        is_broker_owner = (
                obj.broker and
                self.request.user == obj.broker.user
        )
        # ИЛИ является ли пользователь застройщиком-владельцем
        is_developer_owner = (
                obj.developer and
                self.request.user == obj.developer
        )
        return is_broker_owner or is_developer_owner


class SelectPropertyTypeView(LoginRequiredMixin, View):
    template_name = 'properties/select_property_type.html'

    def get(self, request):
        return render(request, self.template_name, {
            'types': PropertyType.objects.all()

        })


class BrokerSearchView(View):
    def get(self, request):
        search = request.GET.get('search', '')
        brokers = User.objects.filter(
            user_type=User.UserType.BROKER  # Используем правильный фильтр по типу
        ).filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(patronymic__icontains=search)
        )[:10]

        brokers_data = [{
            "id": broker.id,
            "name": broker.get_full_name(),  # Полное ФИО
            "avatar": broker.avatar.url if broker.avatar else "/static/default_avatar.png"
        } for broker in brokers]

        return JsonResponse({"brokers": brokers_data})


class SelectListingTypeView(LoginRequiredMixin, View):
    template_name = 'properties/select_listing_type.html'

    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, 'broker_profile'):
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        if not ListingType.objects.exists():
            messages.error(request, "Нет доступных типов размещения. Обратитесь к администратору.")
            return redirect('dashboard')

        # Очищаем предыдущий выбор при новом входе
        if 'selected_listing_type' in request.session:
            del request.session['selected_listing_type']

        form = ListingTypeForm(user=request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = ListingTypeForm(request.POST, user=request.user)
        if form.is_valid():
            listing_type = form.cleaned_data['listing_type']
            request.session['selected_listing_type'] = listing_type.id
            return redirect('properties:select-property-type')  # Указание пространства имён

        return render(request, self.template_name, {'form': form})


class ContactBrokerView(LoginRequiredMixin, View):
    def get(self, request, broker_id, property_id):
        broker_profile = get_object_or_404(BrokerProfile, id=broker_id)
        broker_user = broker_profile.user

        # Проверяем, есть ли уже запрос на контакт
        contact_request = ContactRequest.objects.filter(
            requester=request.user,
            broker=broker_user,
            property_id=property_id
        ).first()

        if contact_request:
            return redirect('contact_request_detail', pk=contact_request.pk)

        # Проверяем, был ли уже оплаченный запрос к этому брокеру по этому объекту
        has_paid_request = Payment.objects.filter(
            user=request.user,
            description__contains=f"Контакт с брокером {broker_id} по объекту {property_id}",
            status='completed'
        ).exists()

        # Создаем запрос
        contact_request = ContactRequest.objects.create(
            requester=request.user,
            broker=broker_user,
            property_id=property_id,
            status='new',
            is_first_message_paid=not has_paid_request
        )

        return redirect('contact_request_detail', pk=contact_request.pk)


class CityAutocompleteView(View):
    def get(self, request):
        query = request.GET.get('query', '')
        api_key = settings.YANDEX_GEOCODER_API_KEY
        url = f"https://geocode-maps.yandex.ru/1.x/?apikey={api_key}&format=json&geocode={query}&kind=locality&results=10"

        try:
            response = requests.get(url)
            data = response.json()
            features = data['response']['GeoObjectCollection']['featureMember']
            cities = []

            for feature in features:
                city = feature['GeoObject']['name']
                address = feature['GeoObject']['description']
                if city not in [c['city'] for c in cities]:
                    cities.append({
                        'city': city,
                        'address': address,
                        'coordinates': feature['GeoObject']['Point']['pos']
                    })

            return JsonResponse({'cities': cities})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# В views.py
class AddressAutocompleteView(View):
    def get(self, request):
        city = request.GET.get('city', '')
        query = request.GET.get('query', '')
        api_key = settings.YANDEX_GEOCODER_API_KEY

        try:
            # Пробуем сначала использовать API Поиска
            search_url = f"https://search-maps.yandex.ru/v1/?apikey={settings.YANDEX_SEARCH_API_KEY}&text={city}+{query}&lang=ru_RU&results=10"
            search_response = requests.get(search_url)

            if search_response.status_code == 200:
                data = search_response.json()
                addresses = [
                    {
                        'address': feature['properties']['name'],
                        'coordinates': feature['geometry']['coordinates']
                    }
                    for feature in data.get('features', [])
                ]
                return JsonResponse({'addresses': addresses})

            # Fallback на геокодер, если API Поиска не доступен
            geocoder_url = f"https://geocode-maps.yandex.ru/1.x/?apikey={api_key}&format=json&geocode={city}+{query}&results=10"
            response = requests.get(geocoder_url)
            data = response.json()

            features = data['response']['GeoObjectCollection']['featureMember']
            addresses = []

            for feature in features:
                geo = feature['GeoObject']
                addresses.append({
                    'address': geo['metaDataProperty']['GeocoderMetaData']['text'],
                    'coordinates': geo['Point']['pos'].split()  # долгота, широта
                })

            return JsonResponse({'addresses': addresses})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class MetroAutocompleteView(View):
    def get(self, request):
        city = request.GET.get('city', 'Москва')  # По умолчанию Москва
        query = request.GET.get('query', '')
        api_key = settings.YANDEX_GEOCODER_API_KEY
        url = f"https://geocode-maps.yandex.ru/1.x/?apikey={api_key}&format=json&geocode={city}&kind=metro&results=50"

        try:
            response = requests.get(url)
            data = response.json()
            features = data['response']['GeoObjectCollection']['featureMember']
            metro_stations = []

            for feature in features:
                if 'name' in feature['GeoObject']:
                    metro_stations.append({
                        'name': feature['GeoObject']['name'],
                        'coordinates': feature['GeoObject']['Point']['pos']
                    })

            # Фильтрация по запросу
            if query:
                metro_stations = [m for m in metro_stations if query.lower() in m['name'].lower()]

            return JsonResponse({'metro_stations': metro_stations[:10]})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
def update_property_address(request):
    try:
        # Логирование входящего запроса
        logger.debug("=" * 50)
        logger.debug("Incoming request to update_property_address")
        logger.debug(f"Request body (raw): {request.body}")

        try:
            data = json.loads(request.body)
            logger.debug(f"Parsed JSON data: {data}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return JsonResponse(
                {'status': 'error', 'message': 'Неверный формат JSON'},
                status=400
            )

        # Проверка наличия property_id
        if 'property_id' not in data:
            logger.error("Missing property_id in request data")
            return JsonResponse(
                {'status': 'error', 'message': 'Отсутствует property_id'},
                status=400
            )

        try:
            property = Property.objects.get(pk=data['property_id'])
            logger.debug(f"Found property: {property.id} - {property.title}")
        except Property.DoesNotExist:
            logger.error(f"Property not found: {data.get('property_id')}")
            return JsonResponse(
                {'status': 'error', 'message': 'Объект не найден'},
                status=404
            )

        # Проверка прав
        if not (request.user == property.broker.user or
                request.user == property.developer or
                request.user.is_admin):
            logger.warning(f"User {request.user.id} doesn't have permissions for property {property.id}")
            return JsonResponse(
                {'status': 'error', 'message': 'Недостаточно прав'},
                status=403
            )

        # Обработка координат
        if data.get('coordinates'):
            logger.debug("-" * 30)
            logger.debug("Processing coordinates data")
            logger.debug(f"Raw coordinates string: {data['coordinates']} (type: {type(data['coordinates'])})")

            try:
                # Разделяем координаты по запятой
                coords = data['coordinates'].split(',')
                logger.debug(f"Split coordinates: {coords}")

                if len(coords) != 2:
                    raise ValueError("Должно быть ровно 2 координаты")

                # Преобразование в float (уже с точкой как разделителем)
                lon, lat = map(float, coords)
                logger.debug(f"Parsed coordinates as floats: lon={lon}, lat={lat}")

                # Создание Point
                point = Point(lon, lat, srid=4326)
                logger.debug(f"Created Point object: {point}")
                logger.debug(f"Point WKT: {point.wkt}")
                logger.debug(f"Point coordinates: x={point.x}, y={point.y}")
                logger.debug(f"Point SRID: {point.srid}")

                # Сохранение в модель
                property.coordinates = point
                logger.debug("Coordinates assigned to property")

            except (ValueError, IndexError, TypeError) as e:
                logger.error(f"Coordinate processing error: {str(e)}", exc_info=True)
                return JsonResponse(
                    {'status': 'error', 'message': f'Некорректный формат координат: {str(e)}'},
                    status=400
                )
        else:
            logger.debug("No coordinates provided in request")

        # Обновление других полей
        property.location = data.get('city', property.location)
        property.address = data.get('address', property.address)
        property.metro_station = data.get('metro_station', property.metro_station)

        try:
            property.save()
            logger.debug("Property successfully saved")
            logger.debug(f"Current coordinates in DB: {property.coordinates}")
            logger.debug(f"Coordinates from DB - x: {property.coordinates.x}, y: {property.coordinates.y}")

            # Получение объекта из БД для проверки
            refreshed_property = Property.objects.get(pk=property.id)
            logger.debug(f"Refreshed coordinates: {refreshed_property.coordinates}")
            logger.debug(
                f"Refreshed coordinates - x: {refreshed_property.coordinates.x}, y: {refreshed_property.coordinates.y}")

        except Exception as e:
            logger.error(f"Error saving property: {str(e)}", exc_info=True)
            return JsonResponse(
                {'status': 'error', 'message': 'Ошибка сохранения данных'},
                status=500
            )

        return JsonResponse({
            'status': 'success',
            'address': property.address,
            'coordinates': {
                'x': property.coordinates.x,
                'y': property.coordinates.y
            }
        })

    except Exception as e:
        logger.error(f"Unexpected error in update_property_address: {str(e)}", exc_info=True)
        return JsonResponse(
            {'status': 'error', 'message': 'Внутренняя ошибка сервера'},
            status=500
        )


class MetroStationsView(View):
    def get(self, request):
        city = request.GET.get('city', '')
        if not city:
            return JsonResponse({'metro_stations': []})

        stations = MetroStation.objects.filter(city__iexact=city).order_by('line', 'name')
        data = {
            'metro_stations': [
                {
                    'name': station.name,
                    'city': station.city,
                    'line': station.line if station.line else 'Другая линия',
                    'line_color': station.line_color if station.line_color else '#cccccc'
                }
                for station in stations
            ]
        }
        return JsonResponse(data)


def home_view(request):
    featured_properties = Property.objects.filter(is_premium=True, is_approved=True)[:6]
    hot_properties = Property.objects.filter(is_hot=True, is_approved=True)[:6]  # Добавьте эту строку

    context = {
        'featured_properties': featured_properties,
        'hot_properties': hot_properties,  # Добавьте эту строку
    }
    return render(request, 'home.html', context)