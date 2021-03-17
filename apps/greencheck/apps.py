from django.apps import AppConfig
import beeline
import os


class GreencheckConfig(AppConfig):
    name = "greencheck"

    def ready(self):
        # If you use uwsgi, gunicorn, celery, or other pre-fork models,
        # see the section below on pre-fork
        # models and do not initialize here.
        beeline.init(
            writekey=os.getenv("HONEYCOMBIO_WRITE_KEY"),
            dataset=os.getenv("HONEYCOMBIO_DATASET"),
            service_name=os.getenv("HONEYCOMBIO_SERVICE_NAME"),
            debug=True,
        )
