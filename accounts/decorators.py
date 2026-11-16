"""Access-level decorators.

Three levels:
  * anonymous      - public pages only
  * user           - signed in (admins count too, since admin is the higher level)
  * admin          - admin role only

Anonymous visitors are sent to the login page; signed-in users without the
right role get a 403 page.
"""

from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from .models import User


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.role not in roles:
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


# Any signed-in app user (normal users and admins).
user_required = role_required(User.Role.USER, User.Role.ADMIN)

# Admins only.
admin_required = role_required(User.Role.ADMIN)
