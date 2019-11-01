from django.contrib import admin

from .models import (
    GreencheckIp,
    GreencheckIpApprove,
)
from .forms import GreencheckIpForm


class GreencheckIpInline(admin.TabularInline):
    extra = 0
    model = GreencheckIp
    classes = ['collapse']
    form = GreencheckIpForm


class GreencheckIpApproveInline(admin.TabularInline):
    model = GreencheckIpApprove
    # filter away records that are already approved.


    def save_model(self, request, obj, form, change):
        """
        Given a model instance save it to the database.
        """
        # depending on the save signature of the approval record
        # handle the approval.

        obj.save()
