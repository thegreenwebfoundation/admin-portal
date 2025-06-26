from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from guardian.admin import AdminUserObjectPermissionsForm, GuardedModelAdminMixin

from ..permissions import manage_datacenter, manage_provider

class ObjectPermissionsAdminMixin(GuardedModelAdminMixin):
    """
    Define a custom mixin for object-level permissions to tweak GuardedModelAdminMixin
    provided by django-guardian.

    Scope of modifications:
    - only admin users can access the permission management views
    - the button to access permission management is only displayed to admins
    - list of available permissions is filtered out to only contain `allowed_permissions`

    Docs: https://django-guardian.readthedocs.io/en/stable/api/guardian.admin.html#guardedmodeladminmixin
    """

    # maintain a list of permissions that are managed via guardian admin
    allowed_permissions = (manage_provider, manage_datacenter)

    # define a custom template to only display the button to manage permissions to admin users
    change_form_template = "admin/guardian/change_form.html"

    def obj_perms_manage_view(self, request, object_pk):
        """
        Override a parent method to only allow admin users
        to access the object permissions view (first screen)
        """
        if request.user.is_admin:
            return super().obj_perms_manage_view(request, object_pk)
        raise PermissionDenied

    def obj_perms_manage_user_view(self, request, object_pk, user_id):
        """
        Override a parent method to only allow admin users
        to access the user permissions management view (second screen)
        """
        if request.user.is_admin:
            return super().obj_perms_manage_user_view(request, object_pk, user_id)
        raise PermissionDenied

    def obj_perms_manage_group_view(self, request, object_pk, group_id):
        """
        Override a parent method to only allow admin users
        to access the group permissions management view (second screen)
        """
        if request.user.is_admin:
            return super().obj_perms_manage_group_view(request, object_pk, group_id)
        raise PermissionDenied

    def get_obj_perms_base_context(self, request, obj):
        """
        Override a parent method in order to filter out permissions
        on the object-level permissions view (first screen)

        Django creates a default set of permissions for each model,
        for example for a Hostinprovider model:
        - add_hostingprovider,
        - change_hostingprovider,
        - delete_hostingprovider,
        - view_hostingprovider.

        We filter out the list of permissions
        to only display those defined in `allowed_permissions`
        """
        context = super().get_obj_perms_base_context(request, obj)
        model_perms = context.get("model_perms")
        managed_perms = model_perms.filter(
            codename__in=[p.codename for p in self.allowed_permissions]
        )
        context.update({"model_perms": managed_perms})
        return context

    class ObjectLevelPermsForm(AdminUserObjectPermissionsForm):
        """
        Define a custom form for managing object-level permissions
        """

        def get_obj_perms_field_choices(self):
            """
            Override a parent method in order to filter out
            the permission list displayed in the permission management form.
            The permissions list will only include those defined in `allowed_permissions`.
            """
            perms = super().get_obj_perms_field_choices()
            managed_perms = [
                p.astuple() for p in ObjectPermissionsAdminMixin.allowed_permissions
            ]
            return [p for p in perms if p in managed_perms]

    def get_obj_perms_manage_user_form(self, request):
        """
        Use custom form for managing user permissions
        """
        return self.ObjectLevelPermsForm

    def get_obj_perms_manage_group_form(self, request):
        """
        Use custom form to manage group permissions
        """
        return self.ObjectLevelPermsForm


class AdminOnlyTabularInline(admin.TabularInline):
    """
    Specifies a TabularInline admin with all permissions for the admin group
    """

    def has_view_permission(self, request, obj=None):
        return request.user.is_admin

    def has_add_permission(self, request, obj=None):
        return request.user.is_admin

    def has_change_permission(self, request, obj=None):
        return request.user.is_admin


class ActionInChangeFormMixin(object):
    """
    Adds custom admin actions
    (https://docs.djangoproject.com/en/4.1/ref/contrib/admin/actions/)
    to the change view of the model.
    """  # noqa: E501

    def response_action(self, request, queryset):
        """
        Prefer HTTP_REFERER for redirect
        """
        response = super(ActionInChangeFormMixin, self).response_action(
            request, queryset
        )
        if isinstance(response, HttpResponseRedirect):
            response["Location"] = request.headers.get("referer", response.url)
        return response

    def change_view(self, request, object_id, extra_context=None):
        """
        Supply custom action form to the admin change_view as a part of context
        """
        actions = self.get_actions(request)
        if actions:
            action_form = self.action_form(auto_id=None)
            action_form.fields["action"].choices = self.get_action_choices(request)
        else:
            action_form = None
        extra_context = extra_context or {}
        extra_context["action_form"] = action_form
        return super(ActionInChangeFormMixin, self).change_view(
            request, object_id, extra_context=extra_context
        )

