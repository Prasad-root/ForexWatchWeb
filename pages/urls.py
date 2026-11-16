from django.urls import path

from . import views

urlpatterns = [
    # Public
    path("", views.home, name="home"),
    path("exchange-rates/", views.rates, name="rates"),
    path("commodities/", views.commodities, name="commodities"),
    path("fuel-prices/", views.fuel, name="fuel"),
    path("stock-market/", views.stocks, name="stocks"),
    path("analytics/", views.analytics, name="analytics"),
    path("datasets/", views.datasets, name="datasets"),
    path("about/", views.about, name="about"),
    path("methodology/", views.methodology, name="methodology"),
    path("contact/", views.contact, name="contact"),
    path("privacy/", views.privacy, name="privacy"),
    path("terms/", views.terms, name="terms"),
    # Signed-in users (dataset download needs an account)
    path("datasets/<slug:slug>/download/", views.dataset_download, name="dataset_download"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("account/", views.user_dashboard, name="user_dashboard"),
    # Admins only
    path("admin-panel/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-panel/users/", views.admin_users, name="admin_users"),
]
