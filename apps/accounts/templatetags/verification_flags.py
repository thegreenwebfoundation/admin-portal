from django import template
from waffle import flag_is_active

register = template.Library()


@register.simple_tag(takes_context=True)
def upstream_section_enabled(context):
    """
    Return True when the upstream-provider section of the basis-for-verification
    step should be rendered.

    The section is shown under the ``verification_basis_v2`` regime (where the
    upstream-provider bases are part of the October 2026 criteria) and also
    under the legacy ``upstream_providers`` feature flag.
    """
    request = context.get("request")
    return (
        flag_is_active(request, "verification_basis_v2")
        or flag_is_active(request, "upstream_providers")
    )
