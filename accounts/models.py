from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        USER = "user", "Normal user"
        ADMIN = "admin", "Admin"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER)

    @property
    def is_app_admin(self):
        return self.role == self.Role.ADMIN

    def save(self, *args, **kwargs):
        # A Django superuser is always an admin in this app.
        if self.is_superuser:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)
