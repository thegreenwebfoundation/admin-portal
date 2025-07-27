from django.urls import reverse

import pytest


def test_visit_styleguide(client):
    """
    When we visit the style guide url, do we get our template ?
    """
    res = client.get(reverse("style-guide"))
    templates = [tpl.name for tpl in res.templates]

    assert res.status_code == 403
    assert "style-guide.html" in templates
