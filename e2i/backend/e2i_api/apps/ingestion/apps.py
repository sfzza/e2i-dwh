from django.apps import AppConfig


class IngestionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "e2i_api.apps.ingestion"
    label = "ingestion"
    verbose_name = "Data Ingestion"

    def ready(self):
        # Import signals here if you create any later
        # from . import signals
        pass
