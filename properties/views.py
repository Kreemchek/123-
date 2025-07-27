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
from django.contrib.gis.measure import Distance
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
from .models import Property, PropertyImage, PropertyType, ListingType
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


class PropertyListView(FilterView):
    model = Property
    template_name = 'properties/property_list.html'
    context_object_name = 'properties'
    filterset_class = PropertyFilter
    paginate_by = 12

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.request.user.is_authenticated and self.request.user.is_admin:
            return queryset

        # Для неаутентифицированных пользователей показываем только одобренные объекты
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_approved=True)

        # Для аутентифицированных пользователей
        else:
            # Если пользователь - брокер
            if self.request.user.is_broker:
                if hasattr(self.request.user, 'broker_profile'):
                    # Брокер видит только свои одобренные объекты
                    queryset = queryset.filter(
                        broker=self.request.user.broker_profile,
                        is_approved=True
                    )
                else:
                    return Property.objects.none()

            # Если пользователь - застройщик
            elif self.request.user.is_developer:
                # Застройщик видит свои объекты
                queryset = queryset.filter(
                    developer=self.request.user
                )

            # Если пользователь - клиент
            else:
                # Клиент видит все одобренные объекты
                queryset = queryset.filter(is_approved=True)

        # Фильтрация по конкретному брокеру (если указан параметр ?broker=id)
        broker_id = self.request.GET.get('broker')
        if broker_id:
            broker = get_object_or_404(BrokerProfile, id=broker_id)

            # Если текущий пользователь - брокер и пытается смотреть чужие объекты
            if self.request.user.is_authenticated and self.request.user.is_broker and self.request.user != broker.user:
                return Property.objects.none()

            queryset = queryset.filter(
                broker=broker,
                is_approved=True
            )

        queryset = queryset.annotate(
            price_per_sqm=ExpressionWrapper(
                F('price') / F('total_area'),
                output_field=FloatField()
            )
        )

        # Поиск по названию или локации
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(location__icontains=search_query)
            )

        # Добавляем расчет расстояния до центра, если нужно
        if 'min_distance_to_center' in self.request.GET or 'max_distance_to_center' in self.request.GET:
            center_point = Point(37.617635, 55.755814, srid=4326)  # Координаты центра Москвы
            queryset = queryset.annotate(
                distance_to_center=Distance('coordinates', center_point))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['YANDEX_MAPS_API_KEY'] = settings.YANDEX_MAPS_API_KEY

        # Добавляем информацию о текущем брокере для фильтра
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
        context['images'] = self.object.images.all()
        context['YANDEX_MAPS_API_KEY'] = settings.YANDEX_MAPS_API_KEY

        # Координаты объекта в формате JSON
        if self.object.coordinates:
            context['coordinates_json'] = json.dumps({
                'x': float(self.object.coordinates.x),
                'y': float(self.object.coordinates.y)
            }, cls=DjangoJSONEncoder)

        # Координаты метро в формате JSON
        if self.object.metro_coordinates:
            context['metro_coordinates_json'] = json.dumps({
                'x': float(self.object.metro_coordinates.x),
                'y': float(self.object.metro_coordinates.y)
            }, cls=DjangoJSONEncoder)

        # Остальной контекст
        if self.request.user.is_authenticated:
            context['is_favorite'] = Favorite.objects.filter(
                user=self.request.user,
                property=self.object
            ).exists()

            context['contact_paid'] = Payment.objects.filter(
                user=self.request.user,
                description__contains=f"Контакт с брокером {self.object.broker.id} по объекту {self.object.id}",
                status='completed'
            ).exists()

            context['existing_request'] = ContactRequest.objects.filter(
                requester=self.request.user,
                broker=self.object.broker.user,
                property=self.object
            ).first()

            context['is_broker'] = self.request.user.user_type == User.UserType.BROKER

        context['has_coordinates'] = bool(self.object.coordinates)

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
                f"Объект успешно создан! С вашего баланса списано {listing_type.price} ₽. Теперь укажите точный адрес объекта."
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
