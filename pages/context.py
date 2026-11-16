from django.conf import settings


def site(request):
    """Make the site name and demo-data flag available in every template."""
    return {"SITE_NAME": settings.SITE_NAME, "DEMO_DATA": settings.DEMO_DATA}
