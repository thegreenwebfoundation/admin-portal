from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import models

types = {
    # 'TGWF\AdminBundle\Entity\Hostingprovider': ('accounts', 'hostingprovider'),
    "TGWF\\AdminBundle\\Entity\\GreencheckAs": ("greencheck", "greencheckasn"),
    # 'TGWF\\AdminBundle\\Entity\\HostingproviderCertificate':
    # 'TGWF\\AdminBundle\\Entity\\DatacenterCertificate'
    # 'TGWF\\AdminBundle\\Entity\\Datacenter'
    # 'TGWF\\AdminBundle\\Entity\\DatacenterHostingprovider'
    "TGWF\\HostingProviderBundle\\Entity\\GreencheckIp": (
        "greencheck",
        "greencheckipapprove",
    ),
    "TGWF\\AdminBundle\\Entity\\GreencheckIp": ("greencheck", "greencheckip"),
    "TGWF\\HostingProviderBundle\\Entity\\GreencheckAs": (
        "greencheck",
        "greencheckasnapprove",
    ),
}


class ExtLog(models.Model):
    object_id = models.IntegerField()
    object_class = models.CharField(max_length=255)
    logged_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "ext_log_entries"


class Command(BaseCommand):
    help = "My shiny new management command."

    def handle(self, *args, **options):
        entries = ExtLog.objects.raw(
            """
            select ext1.id, ext1.object_id, ext1.object_class, logged_at, max_logged
            from `ext_log_entries` ext1
            join (
                SELECT id, Max(logged_at) max_logged, object_id, object_class
                FROM ext_log_entries
                GROUP BY object_id, object_class
            ) ext2 on ext1.id = ext2.id
        """
        )

        for entry in entries:
            app, model_name = types.get(entry.object_class, (None, None))
            if not app:
                continue

            Model = apps.get_model(app, model_name)
            obj = Model.objects.filter(pk=entry.object_id).first()
            if not obj:
                continue

            obj.created = entry.max_logged
            obj.save()
