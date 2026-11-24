from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Read-only view of the admin audit trail in Django's built-in admin."""
    list_display = ("created_at", "user", "section", "action", "target", "detail")
    list_filter = ("section", "action")
    search_fields = ("target", "detail", "user__email")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False