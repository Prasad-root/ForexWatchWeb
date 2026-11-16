from django.contrib import admin
from django.urls import include, path

handler404 = "pages.views.not_found"

urlpatterns = [
    path("django-admin/", admin.site.urls),  # Django's built-in admin (staff only)
    path("accounts/", include("allauth.urls")),  # login, signup, Google OAuth, logout, password reset
    path("", include("pages.urls")),
]
