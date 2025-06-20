import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.deconstruct import deconstructible
from django.utils.regex_helper import _lazy_re_compile
from django.utils.translation import gettext_lazy as _

# TODO: This class is backported from Django 5.1+ and can be removed/replaced on upgrading. See
# https://github.com/django/django/blob/main/django/core/validators.py
@deconstructible
class DomainNameValidator(RegexValidator):
    message = _("Enter a valid domain name. This can include any subdomains (e.g. www.), but should not include the protocol (i.e. http:// or https://) or any content paths (e.g /news/, /about, news-update-2025.html etc.).")
    ul = "\u00a1-\uffff"  # Unicode letters range (must not be a raw string).
    # Host patterns.
    hostname_re = (
        r"[a-z" + ul + r"0-9](?:[a-z" + ul + r"0-9-]{0,61}[a-z" + ul + r"0-9])?"
    )
    # Max length for domain name labels is 63 characters per RFC 1034 sec. 3.1.
    domain_re = r"(?:\.(?!-)[a-z" + ul + r"0-9-]{1,63}(?<!-))*"
    # Top-level domain.
    tld_no_fqdn_re = (
        r"\."  # dot
        r"(?!-)"  # can't start with a dash
        r"(?:[a-z" + ul + "-]{2,63}"  # domain label
        r"|xn--[a-z0-9]{1,59})"  # or punycode label
        r"(?<!-)"  # can't end with a dash
    )
    tld_re = tld_no_fqdn_re + r"\.?"
    ascii_only_hostname_re = r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    ascii_only_domain_re = r"(?:\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*"
    ascii_only_tld_re = (
        r"\."  # dot
        r"(?!-)"  # can't start with a dash
        r"(?:[a-zA-Z0-9-]{2,63})"  # domain label
        r"(?<!-)"  # can't end with a dash
        r"\.?"  # may have a trailing dot
    )

    max_length = 255

    def __init__(self, **kwargs):
        self.accept_idna = kwargs.pop("accept_idna", True)

        if self.accept_idna:
            self.regex = _lazy_re_compile(
                r"^" + self.hostname_re + self.domain_re + self.tld_re + r"$",
                re.IGNORECASE,
            )
        else:
            self.regex = _lazy_re_compile(
                r"^"
                + self.ascii_only_hostname_re
                + self.ascii_only_domain_re
                + self.ascii_only_tld_re
                + r"$",
                re.IGNORECASE,
            )
        super().__init__(**kwargs)

    def __call__(self, value):
        if not isinstance(value, str) or len(value) > self.max_length:
            raise ValidationError(self.message, code=self.code, params={"value": value})
        if not self.accept_idna and not value.isascii():
            raise ValidationError(self.message, code=self.code, params={"value": value})
        super().__call__(value)


validate_domain_name = DomainNameValidator()
