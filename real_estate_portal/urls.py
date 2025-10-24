# real_estate_portal/urls.py
from django.contrib import admin
from django.urls import path, include
from accounts.views import home_view
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view, name='home'),

    path('accounts/', include('accounts.urls')),
    path('brokers/', include('brokers.urls')),
    path('payment/', include('payments.urls')),
    path('developers/', include('developers.urls')),
    path('properties/', include('properties.urls')),  # Убедитесь, что это есть
    path('media-content/', include('media_content.urls')),

    # API endpoints - добавьте их здесь
    path('api/metro-stations/', include('properties.urls')),  # ИЛИ этот вариант

    path('password_reset/',
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset.html'
         ),
         name='password_reset'),
    path('password_reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html'
         ),
         name='password_reset_confirm'),
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ),
         name='password_reset_complete'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)