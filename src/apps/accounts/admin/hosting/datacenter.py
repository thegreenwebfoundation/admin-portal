from django.contrib import admin
from django.utils.safestring import mark_safe

from ... import forms
from ...admin_site import greenweb_admin
from ...forms import (
    DatacenterNoteNoteForm,
)

from ...models import (
    Datacenter,
    DatacenterCertificate,
    DatacenterClassification,
    DatacenterCooling,
    DataCenterLocation,
    DatacenterNote,
    DatacenterSupportingDocument,
)

from ..abstract import ObjectPermissionsAdminMixin


class DatacenterNoteInline(admin.StackedInline):
    """
    A inline for adding notes to Datacentres.
    """

    extra = 0
    model = DatacenterNote
    form = DatacenterNoteNoteForm


class DataCenterSupportingDocumentInline(admin.StackedInline):
    extra = 0
    model = DatacenterSupportingDocument


class DataCenterLocationInline(admin.StackedInline):
    extra = 0
    model = DataCenterLocation


class DatacenterCertificateInline(admin.TabularInline):
    extra = 0
    model = DatacenterCertificate
    classes = ["collapse"]

    # def get_formset(self, request, obj=None, **kwargs):
    # give kwargs a dictionary of widgets to change widgets.


class DatacenterClassificationInline(admin.TabularInline):
    extra = 0
    model = DatacenterClassification
    classes = ["collapse"]


class DatacenterCoolingInline(admin.TabularInline):
    extra = 0
    model = DatacenterCooling
    classes = ["collapse"]


@admin.register(Datacenter, site=greenweb_admin)
class DatacenterAdmin(ObjectPermissionsAdminMixin, admin.ModelAdmin):
    form = forms.DatacenterAdminForm
    inlines = [
        # DatacenterCertificateInline,
        # DatacenterClassificationInline,
        # DatacenterCoolingInline,
        DataCenterSupportingDocumentInline,
        DatacenterNoteInline,
        DataCenterLocationInline,
    ]
    search_fields = ("name",)
    readonly_fields = ["authorised_users"]
    list_display = [
        "name",
        "html_website",
        "country_str",
        "model",
        "pue",
        "classification_names",
        "show_website",
        "certificates_amount",
        "hostingproviders_amount",
    ]
    ordering = ("name",)
    raw_id_fields = ("created_by",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        """
        Assign the current user to any notes added to a datacenter
        in the current request
        """
        formset.save(commit=False)

        if formset.new_objects:
            for new_obj in formset.new_objects:
                if isinstance(new_obj, DatacenterNote):
                    new_obj.added_by = request.user
                    new_obj.save()

        formset.save()

    def get_queryset(self, request, *args, **kwargs):
        qs = super().get_queryset(request, *args, **kwargs)
        qs = qs.prefetch_related(
            "classifications", "datacenter_certificates", "hostingproviders"
        )
        # filter for datacenters that the current user has permissions to
        qs = qs.filter(id__in=[p.id for p in request.user.data_centers])
        return qs

    def get_readonly_fields(self, request, obj=None):
        read_only = super().get_readonly_fields(request, obj)
        if not request.user.is_admin:
            read_only.append("is_listed")
        if obj is not None:
            read_only.append("created_by")
        return read_only

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            (
                "Datacenter info",
                {
                    "fields": (
                        (
                            "name",
                            "website",
                        ),
                        ("country", "created_by"),
                        ("pue", "residualheat"),
                        (
                            "temperature",
                            "temperature_type",
                        ),
                        ("dc12v", "virtual", "greengrid", "is_listed"),
                        ("model",),
                    ),
                },
            ),
        ]
        # include "authorised_users" only for the change view
        users_fieldset = (
            "Authorised data center users",
            {"fields": ("authorised_users",)},
        )
        if obj is not None:
            fieldsets.append(users_fieldset)

        # we only allow green web staff to add hosting providers in the admin
        # to make these changes
        if request.user.is_admin:
            fieldsets.append(
                ("Associated hosting providers", {"fields": ("hostingproviders",)}),
            )
        return fieldsets

    @mark_safe
    def authorised_users(self, obj):
        """
        Returns markup for a list of all users with permissions to manage the Datacenter,
        excluding those in the admin group.
        """
        return "<br>".join(
            [
                f"<a href={u.admin_url}>{u.username}</a>"
                for u in obj.users_explicit_perms
            ]
        )

    def get_inlines(self, request, obj):
        """
        A dynamic check for inlines so we only show some inlines
        to groups with the correct permissions.
        """
        inlines = self.inlines

        if not request.user.is_admin:
            # they're not an admin, return a
            # from the list filtered to remove the 'admin'
            # inlines.
            # We return a filtered list, because changing the state of
            # `inlines` sometimes returns a list to admin users with the
            # admin inlines removed.
            admin_inlines = (DatacenterNoteInline,)
            filtered_inlines = []
            for inline in inlines:
                if inline not in admin_inlines:
                    filtered_inlines.append(inline)
            return filtered_inlines

        return inlines

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}

        if object_id is not None:
            datacentre = self.model.objects.get(id=object_id)
            associated_providers_count = datacentre.hostingproviders.all().count()

            if associated_providers_count:
                extra_context["associated_providers_count"] = associated_providers_count
                extra_context["associated_providers"] = (
                    datacentre.hostingproviders.all()
                )
                extra_context["dc_has_providers"] = True

        return super().change_view(
            request,
            object_id,
            form_url,
            extra_context=extra_context,
        )

    @admin.display(
        description="website"
    )
    @mark_safe
    def html_website(self, obj):
        html = f'<a href="{obj.website}" target="_blank">{obj.website}</a>'
        return html


    @admin.display(
        description="country"
    )
    def country_str(self, obj):
        return obj.country.code


    @admin.display(
        description="Show on website",
        boolean=True,
    )
    def show_website(self, obj):
        return obj.is_listed


    @admin.display(
        description="Classifications"
    )
    def classification_names(self, obj):
        classifications = [c.classification for c in obj.classifications.all()]
        return ", ".join(classifications)


    @admin.display(
        description="Certificates"
    )
    def certificates_amount(self, obj):
        return len(obj.datacenter_certificates.all())


    @admin.display(
        description="Hosters"
    )
    def hostingproviders_amount(self, obj):
        return len(obj.hostingproviders.all())

