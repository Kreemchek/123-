from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User,  Favorite, ContactRequest, DeveloperProfile, \
    BrokerSubscription, ExclusiveProperty , SupportSettings # Импорт новых моделей
from .forms import UserRegistrationForm, UserAdminChangeForm



class CustomUserAdmin(UserAdmin):
    form = UserAdminChangeForm
    add_form = UserRegistrationForm

    list_display = ('username', 'email', 'phone', 'user_type', 'is_staff', 'is_admin')
    list_filter = ('user_type', 'is_staff', 'is_superuser', 'is_verified')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone', 'avatar')}),

        ('Permissions', {
            'fields': ('user_type', 'is_verified', 'is_active', 'is_staff', 'is_superuser', 'is_admin',
                       'groups', 'user_permissions')
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

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'property', 'created_at')
    list_filter = ('user__user_type',)
    raw_id_fields = ('user', 'property')

@admin.register(ContactRequest)
class ContactRequestAdmin(admin.ModelAdmin):
    list_display = ('requester', 'broker', 'property',  'created_at')
    list_filter = ('status', 'broker__user_type')
    raw_id_fields = ('requester',  'property',  'broker', )

@admin.register(DeveloperProfile)
class DeveloperProfileAdmin(admin.ModelAdmin):
    list_display = ('company', 'user', 'is_verified')

@admin.register(BrokerSubscription)
class BrokerSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('broker', 'developer', 'status', 'end_date')

@admin.register(ExclusiveProperty)
class ExclusivePropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'developer', 'price')

admin.site.register(User, CustomUserAdmin)

@admin.register(SupportSettings)
class SupportSettingsAdmin(admin.ModelAdmin):
    list_display = ('support_user',)
    fields = ('support_user',)


