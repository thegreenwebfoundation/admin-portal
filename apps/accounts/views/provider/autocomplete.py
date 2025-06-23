from dal import autocomplete
from dal_select2 import views as dal_select2_views

from ...models import Hostingprovider, Label


class ProviderAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # if a user is not authenticated don't show anything
        if not self.request.user.is_admin:
            return Hostingprovider.objects.none()

        # we only want active hosting providers to allocate to
        qs = Hostingprovider.objects.exclude(archived=True)

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class LabelAutocompleteView(dal_select2_views.Select2QuerySetView):
    def get_queryset(self):
        """
        Return our list of labels, only serving them to internal staff members"""

        if not self.request.user.is_admin:
            return Label.objects.none()

        qs = Label.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs

