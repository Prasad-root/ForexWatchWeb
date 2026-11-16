from django.urls import path

from . import views

# Mounted at /rates/ from config/urls.py:  path("rates/", include("bankrates.urls"))
urlpatterns = [
    path("", views.rates, name="rates"),
    path("data/", views.rates_data, name="rates_data"),
]