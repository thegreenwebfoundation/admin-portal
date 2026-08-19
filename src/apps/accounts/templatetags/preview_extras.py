from django import template
from django.template.defaultfilters import mark_safe, yesno
from django.utils.html import format_html, format_html_join

from apps.accounts.models import (
    DisclosureClaim,
    Hostingprovider,
    Service,
    VerificationBasis,
)

register = template.Library()


@register.filter
def conditional_yesno(value, arg=None):
    """
    Custom template filter that acts like the builtin "yesno" filter,
    but is only applied to certain values: explicitly True, False, None and "".
    """
    if value == "":
        value = None
    if str(value).lower() in ["true", "false", "none"]:
        return yesno(value, arg)
    return value


@register.filter
def render_as_services(value):
    """
    Attempts to map slugs in to service names
    based on a database query.
    """
    tags = Service.objects.filter(slug__in=value)
    if tags:
        return ", ".join([tag.name for tag in tags])
    return None


@register.filter
def render_as_verification_bases(value):
    """
    Attempts to map slugs in to verification basis names
    based on a database query.
    """
    tags = VerificationBasis.objects.filter(slug__in=value).distinct()
    if tags:
        # TODO update to use format_html_join instead of mark_safe directly
        list_items = "\n".join([f"<li>{tag.name}</li>" for tag in tags])
        return mark_safe(f"<ul>{list_items}</ul>")
    return None


@register.filter
def render_as_upstream_providers(value):
    """
    Renders a list of upstream provider selections (list of dicts with
    ``provider`` and ``is_public`` keys) as an HTML list, showing the
    provider name and visibility state.
    """
    if not value:
        return None

    # The value may be a QuerySet (when the private_upstream_linking flag
    # is off and the plain ModelMultipleChoiceField is used) — render
    # names without visibility labels.
    if not isinstance(value, list):
        providers = Hostingprovider.objects.filter(id__in=list(value))
        list_items = format_html(
            "<ul>{}</ul>",
            format_html_join("", "<li>{}</li>", ((p.name,) for p in providers)),
        )
        return list_items

    # If the list items are not dicts (e.g. plain PKs), look up providers.
    if value and not isinstance(value[0], dict):
        providers = list(Hostingprovider.objects.filter(id__in=list(value)))
        list_items = format_html(
            "<ul>{}</ul>",
            format_html_join("", "<li>{}</li>", ((p.name,) for p in providers)),
        )
        return list_items

    # List of dicts with provider instances or PKs.
    # If provider is already a model instance, use it directly.
    if value and all(isinstance(item, dict) and hasattr(item.get("provider"), "name") for item in value):
        list_items = format_html_join(
            "",
            "<li>{} ({})</li>",
            (
                (
                    item["provider"].name,
                    "public" if item.get("is_public", True) else "hidden",
                )
                for item in value
            ),
        )
        return format_html("<ul>{}</ul>", list_items)

    # Provider is a PK — look up the names from the DB.
    provider_ids = [
        p.pk if hasattr(p, "pk") else int(p)
        for item in value
        for p in [item.get("provider")]
        if p is not None
    ]
    providers = {p.id: p for p in Hostingprovider.objects.filter(id__in=provider_ids)}

    def get_pk(p):
        return p.pk if hasattr(p, "pk") else int(p)

    list_items = format_html_join(
        "",
        "<li>{} ({})</li>",
        (
            (
                providers[get_pk(item["provider"])].name,
                "public" if item.get("is_public", True) else "hidden",
            )
            for item in value
            if get_pk(item["provider"]) in providers
        ),
    )
    return format_html("<ul>{}</ul>", list_items)


@register.filter
def exclude_preview_fields(form):
    """
    On preview, exclude fields "id" and "delete" from forms
    """
    return [field for field in form if field.label.lower() not in ["id", "delete"]]


@register.filter
def render_as_regions(value, location_choices=None):
    """
    Render location index values as 'City, Country' strings.
    The value is a list of index strings (e.g. ["0", "2"]).
    location_choices is a list of (index, label) tuples.

    Returns a plain string; Django auto-escapes filter output in
    templates, so user-derived label values are safe by default.
    """
    if not value:
        return None
    if location_choices:
        choice_map = dict(location_choices)
        labels = [choice_map.get(str(v), str(v)) for v in value]
    else:
        labels = [str(v) for v in value]
    return ", ".join(labels)


@register.filter
def render_as_claims(value, claim_choices=None):
    """
    Render claim slugs as human-readable labels.

    The value is a list of DisclosureClaim slugs (e.g.
    ["basis--direct-procurement", "i-would-like-help-confirming-this"]).
    ``claim_choices`` is an optional list of (slug, label) tuples from the
    wizard view; when provided, labels are resolved from it without an extra
    DB hit. Otherwise, claims are looked up in the DB.

    Returns a plain string; Django auto-escapes filter output in
    templates, so admin-editable label values are safe by default.
    """
    if not value:
        return None
    if claim_choices:
        choice_map = dict(claim_choices)
        labels = [choice_map.get(str(v), str(v)) for v in value]
    else:
        claims = DisclosureClaim.objects.filter(slug__in=list(value))
        choice_map = {c.slug: c.label for c in claims}
        labels = [choice_map.get(str(v), str(v)) for v in value]
    list_items = format_html_join(
        "", "<li>{}</li>", ((label,) for label in labels)
    )
    return format_html("<ul>{}</ul>", list_items)


@register.filter
def render_region_scope(form, location_choices=None):
    """
    Render the region scope for a CredentialForm in the preview.
    If region_scope == 'all', show 'All regions'.
    If region_scope == 'specific', show the selected region labels.
    """
    region_scope = None
    locations = []

    # The form may be unbound (preview); read from initial/value
    if hasattr(form, "cleaned_data"):
        region_scope = form.cleaned_data.get("region_scope")
        locations = form.cleaned_data.get("locations", [])
    else:
        scope_field = form.fields.get("region_scope") if hasattr(form, "fields") else None
        if scope_field:
            region_scope = form.initial.get("region_scope", scope_field.initial)
        loc_field = form.fields.get("locations") if hasattr(form, "fields") else None
        if loc_field:
            locations = form.initial.get("locations", [])

    if region_scope == "all":
        return mark_safe("All regions")
    elif region_scope == "specific" and locations:
        return render_as_regions(locations, location_choices)
    elif region_scope == "specific":
        return mark_safe("Specific regions (none selected)")
    return None
