from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Favorite, ContactRequest, DeveloperProfile, \
    BrokerSubscription, SupportSettings, UserAgreement
from .forms import UserRegistrationForm, UserAdminChangeForm
from django.utils.translation import gettext_lazy as _


# Добавляем фильтр для заблокированных пользователей
class BlockedUsersFilter(admin.SimpleListFilter):
    title = _('Блокировка')
    parameter_name = 'is_blocked'

    def lookups(self, request, model_admin):
        return (
            ('blocked', _('Заблокированные')),
            ('unblocked', _('Не заблокированные')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'blocked':
            return queryset.filter(is_blocked=True)
        if self.value() == 'unblocked':
            return queryset.filter(is_blocked=False)


# Создаем отдельный класс для отображения заблокированных пользователей
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    form = UserAdminChangeForm
    add_form = UserRegistrationForm

    list_display = ('username', 'email', 'phone', 'user_type', 'is_staff', 'is_admin', 'is_blocked')
    list_filter = (BlockedUsersFilter, 'user_type', 'is_staff', 'is_superuser', 'is_verified')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone', 'avatar')}),
        ('Permissions', {
            'fields': ('user_type', 'is_verified', 'is_active', 'is_staff', 'is_superuser', 'is_admin',
                       'is_blocked', 'groups', 'user_permissions')
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'phone', 'user_type', 'password1', 'password2'),
        }),
    )
    search_fields = ('username', 'email', 'phone', 'first_name', 'last_name')
    ordering = ('-date_joined',)

    actions = ['block_users', 'unblock_users']

    def block_users(self, request, queryset):
        queryset.update(is_blocked=True)

    block_users.short_description = "Заблокировать выбранных пользователей"

    def unblock_users(self, request, queryset):
        queryset.update(is_blocked=False)

    unblock_users.short_description = "Разблокировать выбранных пользователей"

    def is_admin(self, obj):
        return obj.is_admin

    is_admin.boolean = True
    is_admin.short_description = 'Админ'

    def approve_properties(self, request, queryset):
        queryset.update(is_approved=True)

    approve_properties.short_description = "Одобрить выбранные объекты"

    def reject_properties(self, request, queryset):
        queryset.update(is_approved=False)

    reject_properties.short_description = "Отклонить выбранные объекты"

    # Добавляем метод для отображения только заблокированных пользователей
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.path.endswith('/blocked/'):
            return qs.filter(is_blocked=True)
        return qs

    # Добавляем URL для страницы заблокированных пользователей
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('blocked/', self.admin_site.admin_view(self.changelist_view),
                 name='auth_user_blocked'),
        ]
        return custom_urls + urls

    # Добавляем ссылку в список действий
    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context['show_blocked_link'] = not request.path.endswith('/blocked/')
        return super().changelist_view(request, extra_context=extra_context)


# Остальные модели остаются без изменений
@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'property', 'created_at')
    list_filter = ('user__user_type',)
    raw_id_fields = ('user', 'property')


@admin.register(ContactRequest)
class ContactRequestAdmin(admin.ModelAdmin):
    list_display = ('requester', 'broker', 'property', 'created_at')
    list_filter = ('status', 'broker__user_type')
    raw_id_fields = ('requester', 'property', 'broker')


@admin.register(DeveloperProfile)
class DeveloperProfileAdmin(admin.ModelAdmin):
    list_display = ('company', 'user', 'is_verified')


@admin.register(BrokerSubscription)
class BrokerSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('broker', 'developer', 'status', 'end_date')


@admin.register(SupportSettings)
class SupportSettingsAdmin(admin.ModelAdmin):
    list_display = ('support_user',)
    fields = ('support_user',)


@admin.register(UserAgreement)
class UserAgreementAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'created_at', 'updated_at')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')
    fields = ('title', 'content', 'is_active', 'created_at', 'updated_at')