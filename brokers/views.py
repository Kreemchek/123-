# brokers/views.py
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from .models import BrokerProfile, BrokerReview, ContactRequest
from properties.forms import PropertyForm
from accounts.models import Subscription, Favorite, User
from properties.models import Property
from .forms import BrokerProfileForm, BrokerReviewForm
from django.utils import timezone
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.contrib import messages
from django.views import View
from django_filters.views import FilterView
from .filters import BrokerFilter
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required


class BrokerPropertyListView(LoginRequiredMixin, ListView):
    model = Property
    template_name = 'brokers/property_list.html'
    context_object_name = 'properties'

    def get_queryset(self):
        return Property.objects.filter(broker=self.request.user)


class PropertyCreateWithSubscriptionCheck(LoginRequiredMixin, CreateView):
    model = Property
    form_class = PropertyForm
    template_name = 'properties/property_create_form.html'

    def form_valid(self, form):
        if self.request.user.user_type == 'broker':
            active_sub = Subscription.objects.filter(
                user=self.request.user,
                end_date__gte=timezone.now().date()
            ).exists()

            if not active_sub and form.cleaned_data.get('is_premium'):
                return HttpResponseForbidden("Требуется активная подписка для премиум-объявлений")

        form.instance.user = self.request.user
        return super().form_valid(form)


# brokers/views.py
class BrokerListView(ListView):
    model = BrokerProfile
    template_name = 'brokers/broker_list.html'
    context_object_name = 'brokers'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().filter(
            is_archived=False,
            is_approved=True,
            user__is_verified=True
        )

        # Применяем фильтры из GET-параметров
        search_query = self.request.GET.get('search', '')
        rating_filter = self.request.GET.get('rating', '')
        experience_filter = self.request.GET.get('experience', '')
        services = self.request.GET.getlist('services')
        specializations = self.request.GET.getlist('specialization')

        # Поиск по имени
        if search_query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(user__patronymic__icontains=search_query)
            )

        # Фильтр по рейтингу
        if rating_filter:
            try:
                rating = float(rating_filter)
                queryset = queryset.filter(rating__gte=rating)
            except ValueError:
                pass

        # Фильтр по опыту работы
        if experience_filter:
            if experience_filter == '0-2':
                queryset = queryset.filter(experience__lt=2)
            elif experience_filter == '2-5':
                queryset = queryset.filter(experience__gte=2, experience__lt=5)
            elif experience_filter == '5-10':
                queryset = queryset.filter(experience__gte=5, experience__lt=10)
            elif experience_filter == '10+':
                queryset = queryset.filter(experience__gte=10)

        # Фильтр по услугам
        if services:
            q_objects = Q()
            for service in services:
                q_objects |= Q(services__contains=service)
            queryset = queryset.filter(q_objects)

        # Фильтр по специализации - ИСПРАВЛЕНО
        if specializations:
            q_objects = Q()
            for spec in specializations:
                q_objects |= Q(specializations__contains=spec)  # ← specializations вместо specialization
            queryset = queryset.filter(q_objects)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Добавляем параметры фильтрации в контекст для пагинации
        context['current_filters'] = self.request.GET.urlencode()
        return context
class BrokerDetailView(DetailView):
    model = BrokerProfile
    template_name = 'brokers/broker_detail.html'
    context_object_name = 'broker'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        broker = self.object

        # Получаем отзывы
        context['reviews'] = broker.reviews.filter(is_approved=True)

        # Фильтруем объекты в зависимости от типа пользователя
        if self.request.user.is_authenticated:
            if self.request.user.is_admin or self.request.user.is_superuser:
                # Администратор видит все объекты брокера
                broker_properties = Property.objects.filter(
                    broker=broker
                )
            elif self.request.user.is_broker:
                if self.request.user == broker.user:
                    # Брокер видит только свои одобренные объекты
                    broker_properties = Property.objects.filter(
                        broker=broker,
                        is_approved=True
                    )
                else:
                    # Брокер не должен видеть объекты других брокеров
                    broker_properties = Property.objects.none()
            elif self.request.user.is_developer:
                # Застройщик видит свои объекты
                broker_properties = Property.objects.filter(
                    broker=broker,
                    developer=self.request.user
                )
            else:
                # Клиент видит все одобренные объекты брокера
                broker_properties = Property.objects.filter(
                    broker=broker,
                    is_approved=True
                )
        else:
            # Неаутентифицированные пользователи видят одобренные объекты
            broker_properties = Property.objects.filter(
                broker=broker,
                is_approved=True
            )

        context['broker_properties'] = broker_properties[:4]  # Только 4 объекта для превью
        context['is_admin'] = self.request.user.is_authenticated and (
                    self.request.user.is_admin or self.request.user.is_superuser)

        # Проверка избранного
        is_favorite = False
        user = self.request.user
        if user.is_authenticated and not user.is_broker:
            is_favorite = Favorite.objects.filter(
                user=user,
                broker=broker.user,
                favorite_type='broker'
            ).exists()

        context['is_favorite'] = is_favorite
        return context


class BrokerProfileUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = BrokerProfile
    form_class = BrokerProfileForm
    template_name = 'brokers/broker_update.html'

    def test_func(self):
        return self.request.user == self.get_object().user

    def get_success_url(self):
        return reverse_lazy('broker-detail', kwargs={'pk': self.object.pk})


class BrokerReviewCreateView(LoginRequiredMixin, CreateView):
    model = BrokerReview
    form_class = BrokerReviewForm
    template_name = 'brokers/review_create.html'

    def form_valid(self, form):
        form.instance.broker = get_object_or_404(BrokerProfile, pk=self.kwargs['pk'])
        form.instance.client = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('broker-detail', kwargs={'pk': self.kwargs['pk']})


class BrokerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'brokers/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        broker = self.request.user.broker_profile

        from real_estate_portal.accounts.models import Favorite
        context.update({
            'my_properties': Property.objects.filter(broker=self.request.user),
            'contact_requests': ContactRequest.objects.filter(broker=self.request.user),
            'favorites': Favorite.objects.filter(property__broker=self.request.user),
            'subscriptions': Subscription.objects.filter(user=self.request.user)
        })
        return context

@login_required
def delete_broker_favorite(request, favorite_id):
    favorite = get_object_or_404(Favorite, id=favorite_id, user=request.user, broker__isnull=False)
    broker_name = favorite.broker.get_full_name() if favorite.broker else "Брокер"
    favorite.delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'message': f'Брокер "{broker_name}" удален из избранного'
        })
    else:
        messages.success(request, f'Брокер "{broker_name}" удален из избранного')
        return redirect('dashboard')

