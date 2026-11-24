from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Who did what in the admin panel (deletions, DAG actions, ...)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="+")
    section = models.CharField(max_length=40)          # e.g. "bankrates"
    action = models.CharField(max_length=40)           # e.g. "delete", "dag.trigger"
    target = models.CharField(max_length=200, blank=True)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.section}.{self.action} {self.target}"