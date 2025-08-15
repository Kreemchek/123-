from django.urls import path
from .views import MediaListView, MediaDetailView

app_name = 'media_content'  # Изменил на media_content вместо media

urlpatterns = [
    path('', MediaListView.as_view(), name='list'),
    path('<int:pk>/', MediaDetailView.as_view(), name='detail'),

]