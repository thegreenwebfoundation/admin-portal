from urllib.parse import urlencode
from django.urls import reverse
from django.apps import apps


def get_admin_name(model, name):
    if isinstance(model, str):
        app_name, model_name = model.split(".")
        model = apps.get_model(app_name, model_name)

    name = "{}_{}_{}".format(model._meta.app_label, model._meta.model_name, name)
    return name


def reverse_admin_name(model, name, args=None, kwargs=None, params=None):
    if isinstance(model, str):
        app_name, model_name = model.split(".")
        model = apps.get_model(app_name, model_name)

    name = get_admin_name(model, name)
    url = reverse("admin:{}".format(name), args=args, kwargs=kwargs)
    if params:
        url = f"{url}?{urlencode(params)}"
    return url
