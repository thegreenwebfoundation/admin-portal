from apps.accounts.templatetags.preview_extras import conditional_yesno

import pytest


@pytest.mark.parametrize(
    "input,output",
    [
        ("", "-"),
        (None, "-"),
        (True, "Yes"),
        ("on", "Yes"),
        (False, "No"),
        ("off", "No"),
        ("this value should not be mapped", "this value should not be mapped"),
    ],
)
def test_conditional_yesno(input, output):
    assert conditional_yesno(input, "Yes,No,-") == output
