from datetime import timezone
from cloudinary.models import CloudinaryField
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from properties.models import Property
from cloudinary.uploader import upload, destroy
from cloudinary.models import CloudinaryField
from cloudinary.utils import cloudinary_url
import os
import unicodedata
from django.db import models
from cloudinary.uploader import upload, destroy
from cloudinary.utils import cloudinary_url


class User(AbstractUser):
    email = models.EmailField(_('email address'), unique=True)
    phone = models.CharField(_('Phone Number'), max_length=18, blank=True, null=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)
    first_name = models.CharField(_('first name'), max_length=150, blank=True)
    patronymic = models.CharField(_('patronymic'), max_length=150, blank=True)
    experience = models.IntegerField(
        _('Experience'),
        null=True,
        blank=True,
        help_text="Опыт работы в годах (только для брокеров)"
    )
    is_blocked = models.BooleanField(
        default=False,
        verbose_name='Заблокирован',
        help_text="Определяет, заблокирован ли пользователь"
    )


    is_admin = models.BooleanField(
        default=False,
        verbose_name='Администратор',
        help_text="Определяет, является ли пользователь администратором системы"
    )


    verification_token = models.CharField(max_length=100, blank=True, null=True, verbose_name='Токен верификации')

    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name='Баланс'
    )


    @property
    def is_profile_complete(self):
        if self.user_type == User.UserType.BROKER:
            # Проверка для брокеров
            has_broker_profile = (
                    hasattr(self, 'broker_profile') and
                    self.broker_profile.experience is not None
            )
            return (
                    has_broker_profile and
                    self.last_name and
                    self.first_name and
                    self.phone

            )
        else:
            # Проверка для клиентов и застройщиков
            return all([
                self.user_type,
                self.last_name and self.last_name.strip() != '',
                self.first_name and self.first_name.strip() != '',
            ])

    @property
    def broker_profile(self):
        return getattr(self, 'brokers_brokerprofile', None)

    class UserType(models.TextChoices):
        CLIENT = 'client', _('Client')
        BROKER = 'broker', _('Broker')
        DEVELOPER = 'developer', _('Developer')

    user_type = models.CharField(
        max_length=10,
        choices=UserType.choices,
        default=UserType.CLIENT,
        verbose_name=_('User Type')
    )

    avatar = CloudinaryField('avatar', blank=True, null=True)
    avatar.verbose_name = _('Avatar')
    is_verified = models.BooleanField(default=False, verbose_name=_('Verified'))
    passport = models.CharField(_('Passport Data'), max_length=100, blank=True)

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.get_full_name()} ({self.user_type})"

    def get_full_name(self):
        return f"{self.last_name} {self.first_name} {self.patronymic}".strip()

    @property
    def is_client(self):
        return self.user_type == self.UserType.CLIENT

    @property
    def is_broker(self):
        return self.user_type == self.UserType.BROKER

    @property
    def is_developer(self):
        return self.user_type == self.UserType.DEVELOPER




    @property
    def days_remaining(self):
        return (self.end_date - timezone.now()).days


class UserActivity(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    action = models.CharField(max_length=200)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Активность пользователя'
        verbose_name_plural = 'Активности пользователей'

class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    developer = models.ForeignKey(
        'developers.DeveloperProfile',
        on_delete=models.CASCADE
    )
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'developer')
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return f"{self.user} → {self.developer}"





class Favorite(models.Model):
    FAVORITE_TYPES = [
        ('client', 'Клиентский'),
        ('broker', 'Брокерский')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name = 'account_favorites')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, null=True,
        blank=True )

    broker = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='favorite_brokers'   # Добавьте это поле
    )

    favorite_type = models.CharField(
        max_length=10,
        choices=FAVORITE_TYPES,
        default='client'
    )
    created_at = models.DateTimeField(auto_now_add=True)



class ContactRequest(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('in_progress', 'В обработке'),
        ('completed', 'Завершен'),
    ]

    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts_sent_requests')
    broker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts_received_requests')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, null=True, blank=True, related_name='accounts_contact_requests' )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_consultation = models.BooleanField(default=False)
    is_first_message_paid = models.BooleanField(
        default=True,
        verbose_name="Требуется оплата за первое сообщение"
    )
    first_message_sent = models.BooleanField(
        default=False,
        verbose_name="Первое сообщение отправлено"
    )

    review = models.OneToOneField(
        'brokers.BrokerReview',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cr_review'
    )

    def __str__(self):
        return f"Запрос #{self.id} от {self.requester}"

class Message(models.Model):
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True)
    contact_request = models.ForeignKey(ContactRequest, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    attachment = CloudinaryField('attachment', null=True, blank=True)
    attachment.verbose_name = _('attachment')
    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Сообщение от {self.sender} в запросе #{self.contact_request.id}"


class DeveloperProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='accounts_developer_profile')
    company = models.CharField(max_length=255, verbose_name='Компания')
    description = models.TextField(verbose_name='Описание')
    is_verified = models.BooleanField(default=False, verbose_name='Верифицирован')

    def __str__(self):
        return f"Профиль застройщика: {self.company}"


class BrokerSubscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Активна'),
        ('expired', 'Истекла'),
        ('canceled', 'Отменена')
    ]

    broker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='broker_subscriptions')
    developer = models.ForeignKey(DeveloperProfile, on_delete=models.CASCADE, related_name='subscribers')
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    payment = models.OneToOneField('payments.Payment', on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ('broker', 'developer')

    @property
    def is_active(self):
        return self.status == 'active' and self.end_date >= timezone.now()


class ExclusiveProperty(Property):

    is_exclusive = models.BooleanField(default=True)
    subscription_required = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Эксклюзивный объект'
        verbose_name_plural = 'Эксклюзивные объекты'


class PropertyListing(models.Model):
    broker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='listings')
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    is_featured = models.BooleanField(default=False)
    payment = models.ForeignKey('payments.Payment', on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)

class StatusLog(models.Model):
    contact_request = models.ForeignKey(ContactRequest, on_delete=models.CASCADE, related_name='status_logs')
    status = models.CharField(max_length=20, choices=ContactRequest.STATUS_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.get_status_display()} - {self.timestamp.strftime('%d.%m.%Y %H:%M')}"

class SupportSettings(models.Model):
    support_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Пользователь поддержки",
        help_text="Пользователь, который будет получать вопросы после завершенных чатов"
    )

    class Meta:
        verbose_name = "Настройки поддержки"
        verbose_name_plural = "Настройки поддержки"

    def __str__(self):
        return f"Настройки поддержки (ID: {self.id})"

    @classmethod
    def get_support_user(cls):
        try:
            return cls.objects.first().support_user
        except:
            return None




def transliterate_filename(filename):
    name, ext = os.path.splitext(filename)
    # Упрощенная транслитерация кириллицы в латиницу
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        ' ': '_'
    }
    name = name.lower()
    result = []
    for char in name:
        result.append(translit_map.get(char, char) if char.isalpha() else '_' if char == ' ' else char)
    clean_name = ''.join(result)
    # Удаляем все не-ASCII символы и оставляем только буквы, цифры, подчеркивания и точки
    clean_name = ''.join(c for c in clean_name if c.isalnum() or c in ('_', '-', '.'))
    return f"{clean_name}{ext}"


class UserAgreement(models.Model):
    title = models.CharField(
        max_length=255,
        verbose_name="Название документа"
    )
    content = models.TextField(
        verbose_name="HTML-содержание соглашения",
        help_text="Введите текст соглашения с HTML-разметкой"
    )
    url = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активно"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )

    class Meta:
        verbose_name = "Пользовательское соглашение"
        verbose_name_plural = "Пользовательские соглашения"
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_url(self):
        # Для совместимости с существующим кодом возвращаем URL страницы соглашения
        from django.urls import reverse
        return reverse('user_agreement_detail', kwargs={'pk': self.pk})

    @classmethod
    def get_active_agreement(cls):
        try:
            agreement = cls.objects.filter(is_active=True).first()
            if agreement:
                return {
                    'title': agreement.title,
                    'url': agreement.get_url(),
                    'content': agreement.content
                }
            return None
        except Exception as e:
            print(f"Ошибка при получении соглашения: {str(e)}")
            return None