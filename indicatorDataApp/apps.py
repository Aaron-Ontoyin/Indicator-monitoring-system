from django.apps import AppConfig


class IndicatordataappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'indicatorDataApp'

    def ready(self):
        import indicatorDataApp.signals
