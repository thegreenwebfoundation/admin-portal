from django import forms
from dal_select2.widgets import I18N_PATH
from dal_select2_taggit import widgets as dal_widgets
from taggit_labels.widgets import LabelWidget

# dal_widgets.TaggitSelect2


class NonMinifyingTaggitSelect2(dal_widgets.TaggitSelect2):
    """
    A variant of the TaggitSelect2 widget, that always serves non minified versions of the
    libraries used in the tag autocomplete widget.
    """

    @property
    def media(self):
        """Return JS/CSS resources for the widget."""
        extra = ""
        i18n_name = self._get_language_code()
        i18n_file = ("%s%s.js" % (I18N_PATH, i18n_name),) if i18n_name else ()

        return forms.Media(
            js=(
                "admin/js/vendor/select2/select2.full.js",
                "autocomplete_light/autocomplete_light%s.js" % extra,
                "autocomplete_light/select2%s.js" % extra,
            )
            + i18n_file,
            css={
                "screen": (
                    "admin/css/vendor/select2/select2%s.css" % extra,
                    "admin/css/autocomplete.css",
                    "autocomplete_light/select2.css",
                ),
            },
        )


class NonMinifyingLabelWidget(LabelWidget):

    @property
    def media(self):
        extra = ""
        admin_prefix = "admin/js"
        js = [
            "%s/vendor/jquery/jquery%s.js" % (admin_prefix, extra),
            "%s/jquery.init.js" % admin_prefix,
            "%s/core.js" % admin_prefix,
            "taggit_labels/js/taggit_labels.js",
        ]
        css = {"all": ("taggit_labels/css/taggit_labels.css",)}

        return forms.Media(js=js, css=css)
