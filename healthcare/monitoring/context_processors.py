from django.conf import settings


def frontend_config(request):
    """Makes small config values available to every template without hard-coding them."""
    return {
        "POLL_INTERVAL_MS": getattr(settings, 'FRONTEND_POLL_INTERVAL_MS', 3000),
    }
