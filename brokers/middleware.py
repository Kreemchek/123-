# brokers/middleware.py
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import BrokerProfile

class BrokerProfileCompletionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Список URL, которые доступны без заполненного профиля
        self.exempt_urls = [
            reverse('complete_broker_info'),
            reverse('logout'),
            reverse('dashboard'),  # или ограничить функционал дашборда
            # Добавьте другие URL, которые должны быть доступны
        ]

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Проверяем, аутентифицирован ли пользователь
        if not request.user.is_authenticated:
            return None

        # Проверяем, является ли пользователь брокером
        if not hasattr(request.user, 'user_type') or request.user.user_type != 'broker':
            return None

        # Проверяем, заполнен ли профиль брокера
        if hasattr(request.user, 'broker_profile'):
            broker_profile = request.user.broker_profile
            if not self.is_profile_complete(broker_profile):
                # Проверяем, не пытается ли пользователь получить доступ к exempt URL
                if request.path not in self.exempt_urls and not request.path.startswith('/admin/'):
                    return redirect('complete_broker_info')

        return None

    def is_profile_complete(self, broker_profile):
        """Проверяет, заполнены ли все обязательные поля профиля брокера"""
        required_fields = [
            broker_profile.experience is not None,
            bool(broker_profile.about and broker_profile.about.strip()),
            bool(broker_profile.services),  # Проверяем, что выбраны услуги
            bool(broker_profile.specializations),  # Проверяем, что выбраны специализации
        ]
        return all(required_fields)