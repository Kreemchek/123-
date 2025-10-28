from django.urls import path
from . import views
from .views import (
    PropertyDeleteView, CityAutocompleteView, AddressAutocompleteView,
    MetroAutocompleteView
)

app_name = 'properties'

urlpatterns = [
    # URL для недвижимости
    path('', views.PropertyListView.as_view(), name='property-list'),
    path('<int:pk>/', views.PropertyDetailView.as_view(), name='property-detail'),
    path('create/select-listing-type/', views.SelectListingTypeView.as_view(), name='select-listing-type'),
    path('create/select-type/', views.SelectPropertyTypeView.as_view(), name='select-property-type'),
    path('create/<str:property_type>/', views.PropertyCreateView.as_view(), name='property-create'),
    path('<int:pk>/update/', views.PropertyUpdateView.as_view(), name='property-update'),
    path('<int:pk>/favorite/', views.toggle_favorite, name='property-favorite'),
    path('<int:pk>/delete/', PropertyDeleteView.as_view(), name='property-delete'),
    path('api/brokers/', views.BrokerSearchView.as_view(), name='broker-search'),
    path('contact-broker/<int:broker_id>/<int:property_id>/', views.ContactBrokerView.as_view(), name='contact_broker'),

    # API endpoints
    path('api/cities/', CityAutocompleteView.as_view(), name='city-autocomplete'),
    path('api/addresses/', AddressAutocompleteView.as_view(), name='address-autocomplete'),
    path('api/metro/', MetroAutocompleteView.as_view(), name='metro-autocomplete'),
    path('update-address/', views.update_property_address, name='update_property_address'),
    path('api/metro-stations/', views.MetroStationsView.as_view(), name='metro-stations'),

path('favorite/<int:favorite_id>/delete/', views.delete_favorite, name='favorite-delete'),


]