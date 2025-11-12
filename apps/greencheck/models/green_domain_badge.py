from io import BytesIO
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import models
from django.dispatch import receiver
from model_utils.models import TimeStampedModel

from ..badges.image_generator import GreencheckImageV3
from ..domain_check import GreenDomainChecker
from ...accounts.models import Hostingprovider
from ...accounts.validators import DomainNameValidator

class GreenDomainBadge(TimeStampedModel):
    """
    A cache entry for a GreenWebBadge image - The presence of a row in this table indicates that there
    is a corresponding cached green web badge available in whatever file or object storage service
    is configured in the application. This allows us to decide whether we need to generate an image,
    or simply redirect to the existing cached one.
    """

    domain = models.CharField(
            max_length = 255,
            unique = True,
            null = False,
            blank = False,
            validators=[DomainNameValidator],
            primary_key=True
    )

    path = models.URLField(null = False, blank= False, unique=True)

    @classmethod
    def for_domain(cls, domain):
        """
        Find or create a greenweb badge for a given domain name
        """
        obj, _created = cls.objects.get_or_create(domain = domain)
        return obj

    @classmethod
    def clear_cache(cls, domain):
        """
        Clear any existing cached badges for a given domain name
        """
        if obj := cls.objects.filter(domain=domain).first():
            obj.delete()


    def save_image_file(self, image):
        """
        Hook to save the image file - allows for us to move to different storage easily.
        """
        image_io = BytesIO()
        image.save(image_io, format='PNG')
        image_file = ContentFile(image_io.getvalue())
        self.delete_image_file()
        default_storage.save(self.path, image_file)

    def delete_image_file(self):
        """
        Hook to delete the image file - allows for us to move to different storage easily.
        """
        if default_storage.exists(self.path):
            default_storage.delete(self.path)

    def create_image_file(self):
        """
        This method is called when the badge object is created (via django signals),
        and creates and saves the badge image.
        """
        checker = GreenDomainChecker()

        self.path = self.path_for_domain()

        sitecheck = checker.check_domain(self.domain)

        if sitecheck.hosting_provider_id:
            hosting_provider_name = Hostingprovider.objects.get(pk=sitecheck.hosting_provider_id).name
        else:
            hosting_provider_name = None

        image = GreencheckImageV3.generate_greencheck_image(
                self.domain, sitecheck.green, hosting_provider_name
        )

        self.save_image_file(image)

    @property
    def url(self):
        """
        Returns an absolute, publicly accessible URL to this badge
        """
        return default_storage.url(self.path)

    def path_for_domain(self):
        """
        The path at which the image will be saved. Note that we explicitly persist this
        in the database rather than deriving from the domain name at runtime, as this gives us
        backwards compatibility. If we weren't to do this, then future changes to the
        format of the path in the code would break existing images.
        """
        return f"greenweb_badges/{self.domain}.png"

@receiver(models.signals.pre_save, sender=GreenDomainBadge)
def create_image_file(instance, **_kwargs):
    instance.create_image_file()

@receiver(models.signals.pre_delete, sender=GreenDomainBadge)
def delete_image_file(instance, **_kwargs):
    instance.delete_image_file()

