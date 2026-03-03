from django.core.management.base import BaseCommand
from botocore.exceptions import ClientError
from apps.accounts.models import HostingProviderSupportingDocument


class Command(BaseCommand):
    help = "Ensure that the S3 ACL privacy for all Supporting Documents relects their privacy settings in the Database"

    def handle(self, *args, **options):
        print("Resetting S3 ACL privacy for all documents with attachments")
        documents = HostingProviderSupportingDocument.objects_all.filter(attachment__isnull=False).exclude(attachment__exact="").all()
        for document in documents:
            print(".", end="")
            try:
                document.set_object_store_privacy()
                document.save()
            except ClientError:
                print(f"\n No document found at {document.attachment.name} for document with id {document.id}")
                pass
        print("\nDone.")
