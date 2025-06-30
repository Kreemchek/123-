from datetime import timezone
from django.contrib import admin
from .models import BrokerProfile, BrokerReview
from properties.models import Property

class BrokerPropertyInline(admin.TabularInline):
    model = Property
    fk_name = 'broker'  # Связь через ForeignKey 'broker' в модели Property
    extra = 0  # Не показывать пустые формы для новых объектов
    fields = (
        'title',
        'property_type',
        'price',
        'monthly_price',
        'daily_price',
        'location',
        'status',
        'is_approved',
        'created_at',
        'view_link'
    )
    readonly_fields = ('title', 'property_type', 'price', 'monthly_price', 'daily_price',
                      'location', 'created_at', 'view_link')
    show_change_link = True  # Показывать ссылку "Изменить"
    ordering = ('-created_at',)  # Сортировка по дате создания (новые сверху)

    def view_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        url = reverse('admin:properties_property_change', args=[obj.id])
        return format_html('<a href="{}">Просмотр</a>', url)
    view_link.short_description = 'Действие'


    def has_add_permission(self, request, obj=None):
        return False  # Запрещаем добавление новых объектов через inline

    def has_change_permission(self, request, obj=None):
        return True  # Разрешаем просмотр всем

    def has_delete_permission(self, request, obj=None):
        return False  # Запрещаем удаление через inline

class BrokerReviewInline(admin.TabularInline):
    model = BrokerReview
    extra = 0
    fields = ('client', 'rating', 'comment', 'created_at', 'is_approved')
    readonly_fields = ('client', 'created_at')
    show_change_link = True

@admin.register(BrokerProfile)
class BrokerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'rating', 'experience', 'is_approved', 'is_archived', 'get_properties_count')
    list_filter = ('is_approved', 'is_archived')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    list_editable = ('is_approved', 'is_archived')
    fieldsets = (
        (None, {
            'fields': ('user', 'is_approved')
        }),
        ('Информация', {
            'fields': ('experience', 'about', 'avatar', 'rating')
        }),
        ('Подписка', {
            'fields': ('subscription_expiry', 'is_archived', 'archived_at')
        }),
    )
    readonly_fields = ('rating', 'archived_at')
    inlines = [BrokerPropertyInline, BrokerReviewInline]

    def get_properties_count(self, obj):
        return Property.objects.filter(broker=obj).count()
    get_properties_count.short_description = 'Кол-во объектов'
    get_properties_count.admin_order_field = 'user__property_set'  # Для возможности сортировки

    def get_inline_instances(self, request, obj=None):
        if obj:
            for inline in self.inlines:
                if hasattr(inline, 'parent_obj'):
                    inline.parent_obj = obj
        return super().get_inline_instances(request, obj)

    def save_model(self, request, obj, form, change):
        if obj.is_archived and not obj.archived_at:
            obj.archived_at = timezone.now()
        elif not obj.is_archived and obj.archived_at:
            obj.archived_at = None
        super().save_model(request, obj, form, change)

@admin.register(BrokerReview)
class BrokerReviewAdmin(admin.ModelAdmin):
    list_display = ('broker', 'client', 'rating', 'created_at', 'is_approved')
    list_filter = ('is_approved', 'rating')
    search_fields = ('broker__user__username', 'client__username', 'comment')
    list_editable = ('is_approved',)
    readonly_fields = ('created_at',)