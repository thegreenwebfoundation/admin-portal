from django.contrib import admin, messages
from django.contrib.auth.admin import Group, GroupAdmin, UserAdmin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.safestring import mark_safe

from ..admin_site import greenweb_admin
from ..forms import CustomUserCreationForm
from ..models import User

@admin.register(Group, site=greenweb_admin)
class CustomGroupAdmin(GroupAdmin):
    pass


@admin.register(User, site=greenweb_admin)
class CustomUserAdmin(UserAdmin):
    """
    Custom user admin form, with modifications for us by internal
    green web staff members.
    """

    # we override the normal User Creation Form, because we want to support
    # staff members creating users from inside the admin
    add_form = CustomUserCreationForm

    model = User
    search_fields = ("username", "email")
    list_display = ["username", "email", "last_login"]
    list_filter = ("is_superuser", "is_active", "groups")
    readonly_fields = ("managed_providers", "managed_datacenters")

    def change_view(self, request, object_id, form_url="", extra_context=None):
        """
        For non-admin users who are trying to access a change page for another user
        redirect them to the main admin page and display an error message.

        Default mechanism of this method in ModelAdmin has the redirect too,
        but it triggers get_queryset, which results in the message saying that the object was deleted.
        This might be confusing to the users.
        """
        if not request.user.is_admin and str(request.user.id) != object_id:
            msg = "You do not have permissions to visit that page"
            self.message_user(request, msg, messages.WARNING)
            url = reverse("admin:index", current_app=self.admin_site.name)
            return HttpResponseRedirect(url)
        return super().change_view(request, object_id, form_url, extra_context)

    def get_queryset(self, request, *args, **kwargs):
        """
        This filter the view to only show the current user,
        except if you are internal staff
        """
        qs = super().get_queryset(request, *args, **kwargs)
        if not request.user.is_admin:
            qs = qs.filter(pk=request.user.pk)
        return qs

    @mark_safe
    def _managed_objects_markup(self, user, object_list, objects_name):
        """
        A helper method that returns markup for a list of all objects
        that the user has permissions to manage,
        providing a custom explanation for the admin users.
        """
        object_list_markup = "<br>".join(
            [f"<a href={obj.admin_url}>{obj.name}</a>" for obj in object_list]
        )

        if not user.is_admin:
            return object_list_markup

        admin_explanation = f"""
            <p>
            This user is an admin - they have access to manage all the {objects_name} in the database.<br>
            Below is a list of those {objects_name} for which a permission has been granted explicitly for the user,
            rather than based on the admin role.
            </p><br>
            """
        return admin_explanation + object_list_markup

    @mark_safe
    def managed_providers(self, obj):
        """
        Returns markup for a list of all hosting providers that the user has permissions to manage
        """
        return self._managed_objects_markup(
            obj, obj.hosting_providers_explicit_perms, "providers"
        )

    @mark_safe
    def managed_datacenters(self, obj):
        """
        Returns markup for a list of all data centers that the user has permissions to manage
        """
        return self._managed_objects_markup(
            obj, obj.data_centers_explicit_perms, "data centers"
        )

    def get_fieldsets(self, request, obj=None, *args, **kwargs):
        """Return different fieldsets depending on the user signed in"""
        # this is the normal username and password combo for
        # creating a user.
        top_row = (None, {"fields": ("username", "password")})

        # followed by the stuff a user might change themselves
        contact_deets = ("Personal info", {"fields": ("email",)})

        # what we show for internal staff
        staff_fieldsets = (
            "User status and group membership",
            {
                "fields": ("is_active", "groups"),
            },
        )

        # our usual set of forms to show for users
        default_fieldset = [top_row, contact_deets]

        # show managed providers and datacenters on the change view only
        providers_fieldset = ("Hosting providers", {"fields": ("managed_providers",)})
        datacenters_fieldset = ("Data centers", {"fields": ("managed_datacenters",)})
        if obj is not None:
            default_fieldset.append(providers_fieldset)
            default_fieldset.append(datacenters_fieldset)

        # serve the extra staff fieldsets for creating users
        if request.user.is_admin:
            return (*default_fieldset, staff_fieldsets)

        # allow an override for super users
        if request.user.is_superuser:
            return (
                *default_fieldset,
                staff_fieldsets,
                (
                    "User status and group membership",
                    {
                        "fields": (
                            "is_active",
                            "is_superuser",
                            "groups",
                        ),
                    },
                ),
            )

        return default_fieldset
