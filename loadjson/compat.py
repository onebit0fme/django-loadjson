
try:
    from django.apps import apps
    get_model = apps.get_model
except ImportError:
    from django.db.models import get_model
