from urllib.parse import urlencode
from django.urls import reverse
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from anymail.message import AnymailMessage
from .models import Service

import smtplib
import logging
import requests

logger = logging.getLogger(__name__)


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


def tags_choices():
    return [(tag.id, tag.name) for tag in Service.objects.all()]


def send_email(address, subject, context, template_txt, template_html=None, bcc=None):
    """
    Sends an email based on a template and context to render.

    Fire and forget - does not re-raise exceptions from the email client.
    """

    email_body = render_to_string(template_txt, context=context)

    msg = AnymailMessage(
        subject=subject,
        body=email_body,
        to=[address],
        cc=["support@greenweb.org"],
    )

    if bcc:
        msg.bcc.append(bcc)

    if template_html:
        email_html = render_to_string(template_html, context=context)
        msg.attach_alternative(email_html, "text/html")

    try:
        msg.send()
    except smtplib.SMTPException as err:
        logger.warn(
            f"Failed to send because of {err}. See https://docs.python.org/3/library/smtplib.html for more"  # noqa
        )
    except Exception:
        logger.exception("Unexpected fatal error sending email: {err}")

def validate_carbon_txt_for_domain(domain, timeout=3):
    try:
        response = requests.post(settings.CARBON_TXT_VALIDATOR_API_ENDPOINT, json={ "domain": domain }, timeout=timeout)
    except requests.exceptions.RequestException as e:
        raise ValidationError(f"Error validating carbon.txt: {e.__doc__}")
    json = response.json()
    success = json["success"]
    if not success:
        message = ", ".join(json.get("errors", []))
        details_url = f"{settings.CARBON_TXT_VALIDATOR_UI_URL}?auto=true&domain={domain}"
        full_message = (
            f"Error fetching carbon.txt: {message}."
            f"<br /><a class=\"text-purple\" href=\"{details_url}\" target=\"_blank\">More details (opens in new tab)</a>."
        )
        raise ValidationError(mark_safe(full_message))

