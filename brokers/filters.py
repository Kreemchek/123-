# brokers/filters.py
import django_filters
from django import forms
from django.db.models import Q
from .models import BrokerProfile


class BrokerFilter(django_filters.FilterSet):
    # Поиск по имени
    search = django_filters.CharFilter(
        method='filter_search',
        label='Поиск по имени',
        widget=forms.TextInput(attrs={
            'placeholder': 'Поиск по имени...',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
        })
    )

    # Фильтр по услугам
    services = django_filters.MultipleChoiceFilter(
        choices=BrokerProfile.SERVICES_CHOICES,
        method='filter_services',
        label='Услуги',
        widget=forms.CheckboxSelectMultiple(
            attrs={'class': 'rounded border-gray-300 text-blue-600 focus:ring-blue-500'})
    )

    # Фильтр по опыту работы
    EXPERIENCE_CHOICES = [
        ('0-2', 'Менее 2 лет'),
        ('2-5', '2-5 лет'),
        ('5-10', '5-10 лет'),
        ('10+', 'Более 10 лет'),
    ]

    experience = django_filters.ChoiceFilter(
        choices=EXPERIENCE_CHOICES,
        method='filter_experience',
        label='Опыт работы',
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
        })
    )

    # Фильтр по специализации
    specialization = django_filters.MultipleChoiceFilter(
        choices=BrokerProfile.SPECIALIZATION_CHOICES,
        method='filter_specialization',
        label='Специализация',
        widget=forms.CheckboxSelectMultiple(
            attrs={'class': 'rounded border-gray-300 text-blue-600 focus:ring-blue-500'})
    )

    # Фильтр по рейтингу
    rating = django_filters.NumberFilter(
        field_name='rating',
        lookup_expr='gte',
        label='Рейтинг от',
        widget=forms.NumberInput(attrs={
            'min': 1, 'max': 5, 'step': 0.1,
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': '0.0'
        })
    )

    class Meta:
        model = BrokerProfile
        fields = ['search', 'services', 'experience', 'specialization', 'rating']

    def filter_search(self, queryset, name, value):
        """Поиск по ФИО брокера"""
        if value:
            return queryset.filter(
                Q(user__first_name__icontains=value) |
                Q(user__last_name__icontains=value) |
                Q(user__patronymic__icontains=value)
            )
        return queryset

    def filter_services(self, queryset, name, value):
        """Фильтр по услугам"""
        if value:
            q_objects = Q()
            for service in value:
                q_objects |= Q(services__contains=service)
            return queryset.filter(q_objects)
        return queryset

    def filter_experience(self, queryset, name, value):
        """Фильтр по опыту работы"""
        if value:
            if value == '0-2':
                return queryset.filter(experience__lt=2)
            elif value == '2-5':
                return queryset.filter(experience__gte=2, experience__lt=5)
            elif value == '5-10':
                return queryset.filter(experience__gte=5, experience__lt=10)
            elif value == '10+':
                return queryset.filter(experience__gte=10)
        return queryset

    def filter_specialization(self, queryset, name, value):
        """Фильтр по специализации"""
        if value:
            q_objects = Q()
            for spec in value:
                # Для JSONField лучше искать значение в массиве
                q_objects |= Q(specializations__contains=[spec])
            return queryset.filter(q_objects)
        return queryset