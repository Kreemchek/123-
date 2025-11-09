from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import User
from properties.models import Property
from cloudinary.models import CloudinaryField
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


class BrokerProfile(models.Model):
    """Профиль брокера недвижимости"""

    # Константы для услуг
    SERVICES_CHOICES = [
        ('consultation', 'Консультации'),
        ('selection', 'Подбор объекта'),
        ('transaction', 'Проведение сделок'),
        ('legal', 'Юридическое сопровождение'),
    ]

    # Константы для специализации
    SPECIALIZATION_CHOICES = [
        ('residential', 'Жилая недвижимость'),
        ('commercial', 'Коммерческая недвижимость'),
        ('country', 'Загородная недвижимость'),
        ('rent', 'Аренда'),
        ('mortgage', 'Ипотека'),
    ]

    services = models.JSONField(
        default=list,
        verbose_name='Услуги',
        help_text='Список предоставляемых услуг'
    )

    specializations = models.JSONField(
        default=list,
        verbose_name='Специализация',
        help_text='Список специализаций'
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='broker_profile',
        verbose_name=_('Пользователь')
    )

    experience = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Опыт работы (лет)')
    )

    about = models.TextField(
        verbose_name=_('О себе'),
        blank=True
    )
    avatar = CloudinaryField('avatar', blank=True, null=True)
    avatar.verbose_name = _('Avatar')

    is_archived = models.BooleanField(
        default=False,
        verbose_name=_('В архиве')
    )
    archived_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Дата архивации')
    )
    subscription_expiry = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Окончание подписки')
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.0,
        verbose_name=_('Рейтинг')
    )
    is_approved = models.BooleanField(
        default=False,
        verbose_name=_('Подтвержден')
    )

    class Meta:
        verbose_name = _('Профиль брокера')
        verbose_name_plural = _('Профили брокеров')
        ordering = ['-rating']

    def __str__(self):
        return f"Профиль брокера: {self.user.get_full_name()}"

    def active_properties(self):
        return self.user.broker_properties.filter(status='active', is_approved=True)

    active_properties.short_description = _('Активные объекты')

    def update_rating(self):
        """Обновляет рейтинг брокера на основе одобренных отзывов"""
        approved_reviews = self.reviews.filter(is_approved=True)

        if approved_reviews.exists():
            avg_rating = approved_reviews.aggregate(models.Avg('rating'))['rating__avg']
            self.rating = round(float(avg_rating), 2)  # Округляем до 2 знаков
        else:
            self.rating = 0.0

        self.save(update_fields=['rating'])

    def get_services_display(self):
        """Возвращает отображаемые названия услуг"""
        return [dict(self.SERVICES_CHOICES).get(service, service) for service in self.services]

    def get_specializations_display(self):  # Измените название метода!
        """Возвращает отображаемые названия специализаций"""
        return [dict(self.SPECIALIZATION_CHOICES).get(spec, spec) for spec in self.specializations]


class BrokerReview(models.Model):
    """Отзывы о брокерах"""

    broker = models.ForeignKey(
        BrokerProfile,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_('Брокер')
    )
    client = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('Клиент')
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        verbose_name=_('Оценка')
    )
    comment = models.TextField(
        verbose_name=_('Комментарий')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата создания')
    )
    is_approved = models.BooleanField(
        default=False,
        verbose_name=_('Одобрен')
    )
    contact_request = models.OneToOneField(
        'accounts.ContactRequest',  # Указываем явно из-за разных приложений
        on_delete=models.CASCADE,
        related_name='br_contact_request',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = _('Отзыв о брокере')
        verbose_name_plural = _('Отзывы о брокерах')
        ordering = ['-created_at']
        unique_together = ('contact_request',)


    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Обновляем рейтинг брокера при сохранении отзыва
        if self.is_approved:
            self.broker.update_rating()

    def delete(self, *args, **kwargs):
        broker = self.broker
        super().delete(*args, **kwargs)
        # Обновляем рейтинг брокера при удалении отзыва
        broker.update_rating()

    def __str__(self):
        return f"Отзыв {self.client} для {self.broker} ({self.rating}/5)"



# Сигналы для автоматического обновления рейтинга
@receiver(post_save, sender=BrokerReview)
def update_broker_rating_on_save(sender, instance, **kwargs):
    """Обновляет рейтинг брокера при сохранении отзыва"""
    if instance.is_approved:
        instance.broker.update_rating()

@receiver(post_delete, sender=BrokerReview)
def update_broker_rating_on_delete(sender, instance, **kwargs):
    """Обновляет рейтинг брокера при удалении отзыва"""
    instance.broker.update_rating()


class ContactRequest(models.Model):
    # УПРОЩЕННЫЕ СТАТУСЫ БЕЗ ОПЛАТЫ
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('in_progress', 'В обработке'),
        ('completed', 'Завершено')
    ]

    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='brokers_sent_requests')
    broker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='brokers_received_requests')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='brokers_contact_requests', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    # УДАЛЕНО: payment_amount, transaction_id
    is_consultation = models.BooleanField(default=False)

    def __str__(self):
        return f"Запрос #{self.id} ({self.get_status_display()})"