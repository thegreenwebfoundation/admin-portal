from django.contrib.admin.sites import AdminSite
from django.contrib.auth.forms import AuthenticationForm


class GreenWebAdmin(AdminSite):
    # This is a standard authentication form that allows non-staff users
    form = AuthenticationForm
    site_header = 'Green Web Admin'
    index_template = 'admin_index.html'
    site_header = 'Green Web Admin'

    def has_permission(self, request):
        """
        Just check that the user is active, we want
        non-staff users to be able to access admin too.
        """
        return request.user.is_active


greenweb_admin = GreenWebAdmin(name='greenweb_admin')
