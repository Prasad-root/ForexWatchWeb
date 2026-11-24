from django.urls import path
from . import views

urlpatterns = [
    path("", views.overview, name="cp_overview"),
    path("", views.overview, name="admin_dashboard"), 

    path("api-keys/", views.placeholder, {"key": "api_keys"}, name="cp_api_keys"),
    path("commodities/", views.placeholder, {"key": "commodities"}, name="cp_commodities"),
    path("fuel/", views.placeholder, {"key": "fuel"}, name="cp_fuel"),
    path("stocks/", views.placeholder, {"key": "stocks"}, name="cp_stocks"),

    path("bank-rates/", views.bankrates, name="cp_bankrates"),
    path("bank-rates/detail/", views.bankrates_detail, name="cp_bank_detail"),
    path("bank-rates/delete/request/", views.bankrates_delete_request, name="cp_bank_delete_request"),
    path("bank-rates/delete/confirm/", views.bankrates_delete_confirm, name="cp_bank_delete_confirm"),
    path("bank-rates/dag/status/", views.bankrates_dag_status, name="cp_bank_dag_status"),
    path("bank-rates/dag/action/", views.bankrates_dag_action, name="cp_bank_dag_action"),
]