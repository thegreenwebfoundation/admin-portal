from apps.accounts.templatetags.preview_extras import (
    conditional_yesno,
    render_as_services,
)
import pytest


@pytest.mark.parametrize(
    "input,output",
    [
        ("", "-"),
        (None, "-"),
        (True, "Yes"),
        (False, "No"),
        ("this value should not be mapped", "this value should not be mapped"),
    ],
)
def test_conditional_yesno(input, output):
    assert conditional_yesno(input, "Yes,No,-") == output


@pytest.fixture
def service_tags(db, tag_factory):
    tag_factory.create(slug="slug1", name="Service 1")
    tag_factory.create(slug="slug2", name="Service 2")
    tag_factory.create(slug="slug3", name="Service 3")


@pytest.mark.parametrize(
    "input,output",
    [
        (["slug1"], "Service 1"),
        (["slug2", "xyz"], "Service 2"),
        (["slug2", "slug3"], "Service 2, Service 3"),
        (["xyz"], None),
        ([], None),
        ("xyz", None),
    ],
)
def test_render_as_services(input, output, service_tags):
    assert render_as_services(input) == output
