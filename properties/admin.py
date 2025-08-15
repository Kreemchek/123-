from django.contrib import admin
from django import forms
from .models import PropertyType, Property, PropertyImage, ListingType
from accounts.models import User
from brokers.models import BrokerProfile  # Добавьте этот импорт

class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1
    fields = ('image', 'order')
    ordering = ('order',)

class BrokerChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.user.get_full_name() if hasattr(obj, 'user') else str(obj)


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    actions = ['approve_properties', 'mark_as_hot', 'unmark_as_hot']
    list_display = (
    'title', 'price', 'property_type', 'status', 'get_broker_name', 'developer', 'is_approved', 'is_hot', 'created_at')
    list_filter = ('status', 'property_type', 'is_approved', 'is_premium', 'is_hot')
    search_fields = (
    'title', 'description', 'address', 'broker__user__last_name', 'broker__user__first_name', 'developer__username')
    list_editable = ('is_approved', 'status', 'is_hot')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'property_type', 'is_approved', 'status', 'is_hot')
        }),
        ('Характеристики', {
            'fields': ('price', 'living_area', 'total_area', 'rooms', 'location', 'address')
        }),
        ('Метаданные', {
            'fields': ('broker', 'developer', 'is_premium', 'main_image')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [PropertyImageInline]

    def get_broker_name(self, obj):
        if obj.broker and obj.broker.user:
            return obj.broker.user.get_full_name()
        return '-'

    get_broker_name.short_description = 'Брокер'
    get_broker_name.admin_order_field = 'broker__user__last_name'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "broker":
            kwargs["queryset"] = BrokerProfile.objects.all().order_by('user__last_name', 'user__first_name')
            kwargs["form_class"] = BrokerChoiceField
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('broker__user', 'developer', 'property_type')

    def approve_properties(self, request, queryset):
        queryset.update(is_approved=True, status='active')

    approve_properties.short_description = "Одобрить выбранные объекты"

    def mark_as_hot(self, request, queryset):
        queryset.update(is_hot=True)

    mark_as_hot.short_description = "Пометить как горячее предложение"

    def unmark_as_hot(self, request, queryset):
        queryset.update(is_hot=False)

    unmark_as_hot.short_description = "Снять пометку горячего предложения"

    def save_model(self, request, obj, form, change):
        if 'is_approved' in form.changed_data and obj.is_approved:
            obj.status = 'active'
        super().save_model(request, obj, form, change)

@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ('property', 'image', 'order')
    list_editable = ('order',)
    list_filter = ('property__status',)
    search_fields = ('property__title',)

@admin.action(description='Одобрить выбранные объекты')
def approve_properties(modeladmin, request, queryset):
    queryset.update(is_approved=True)

@admin.register(PropertyType)
class PropertyTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'icon')
    search_fields = ('name',)

@admin.register(ListingType)
class ListingTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_days', 'is_featured')
    list_filter = ('is_featured',)
    search_fields = ('name', 'description')


