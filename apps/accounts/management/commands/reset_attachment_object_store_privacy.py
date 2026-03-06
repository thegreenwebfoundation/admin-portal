from django.core.management.base import BaseCommand
from botocore.exceptions import ClientError
from apps.accounts.models import HostingProviderSupportingDocument


class Command(BaseCommand):
    help = "Ensure that the S3 ACL privacy for all Supporting Documents reflects their privacy settings in the Database"

    def handle(self, *args, **options):
        self.stdout.write("Resetting S3 ACL privacy for all documents with attachments")
        documents = HostingProviderSupportingDocument.objects_all.filter(attachment__isnull=False).exclude(attachment__exact="").all()
        for document in documents:
            try:
                document.set_object_store_privacy()
                document.save()
                self.stdout.write(".", ending="")
            except ClientError:
                self.stderr.write(self.style.ERROR(f"\n No document found at {document.attachment.name} for document with id {document.id}"))
                pass
        self.stdout.write(self.style.SUCCESS("\nDone."))
