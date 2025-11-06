import decimal
import ipaddress

from django import forms
from django.core import exceptions, validators
from django.db.models.fields import Field
from django.utils.functional import cached_property
from django.utils.text import capfirst

class IpAddressField(Field):
    default_error_messages = {
        "invalid": "'%(value)s' value must be a valid IpAddress.",
    }
    description = "IpAddress"
    empty_strings_allowed = False

    def __init__(self, *args, **kwargs):
        kwargs.pop("max_digits", None)
        kwargs.pop("decimal_places", None)
        self.max_digits = 39
        self.decimal_places = 0
        super().__init__(*args, **kwargs)
        self.validators = []

    def check(self, **kwargs):
        errors = super().check(**kwargs)
        return errors

    @cached_property
    def validators(self):
        return super().validators + [
            validators.DecimalValidator(self.max_digits, self.decimal_places)
        ]

    @cached_property
    def context(self):
        return decimal.Context(prec=self.max_digits)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.max_digits is not None:
            kwargs["max_digits"] = self.max_digits
        if self.decimal_places is not None:
            kwargs["decimal_places"] = self.decimal_places
        return name, path, args, kwargs

    def to_python(self, value):
        if value is None:
            return value
        try:
            if hasattr(value, "quantize"):
                return ipaddress.ip_address(int(value))
            return ipaddress.ip_address(value)
        except (TypeError, ValueError):
            raise exceptions.ValidationError(
                self.error_messages["invalid"],
                code="invalid",
                params={"value": value},
            )

    def get_db_prep_save(self, value, connection):
        value = self.get_prep_value(value)
        return connection.ops.adapt_decimalfield_value(
            value, self.max_digits, self.decimal_places
        )

    def get_prep_value(self, value):
        if value is not None:
            if isinstance(value, str):
                value = ipaddress.ip_address(value)

            return decimal.Decimal(int(value))
        return None

    def from_db_value(self, value, _expression, _connection):
        if value is None:
            return value
        return str(ipaddress.ip_address(int(value)))

    def get_internal_type(self):
        return "DecimalField"

    def formfield(self, form_class=None, choices_form_class=None, **kwargs):
        """Return a django.forms.Field instance for this field."""
        defaults = {
            "required": not self.blank,
            "label": capfirst(self.verbose_name),
            "help_text": self.help_text,
        }
        if self.has_default():
            if callable(self.default):
                defaults["initial"] = self.default
                defaults["show_hidden_initial"] = True
            else:
                defaults["initial"] = self.get_default()
        defaults.update(kwargs)
        if form_class is None:
            form_class = forms.CharField
        return form_class(**defaults)


