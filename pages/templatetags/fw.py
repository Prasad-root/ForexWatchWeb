from django import template

register = template.Library()


@register.filter
def absval(value):
    """Absolute value, for showing '▼ 0.45%' instead of '▼ -0.45%'."""
    try:
        return abs(value)
    except TypeError:
        return value
