from io import BytesIO
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import models
from django.dispatch import receiver
from model_utils.models import TimeStampedModel

from ..badges.image_generator import GreencheckImageV3, GreencheckImageV2
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
            null = False,
            blank = False,
            validators=[DomainNameValidator],
    )

    path = models.URLField(null = False, blank= False, unique=True)
    legacy = models.BooleanField(null=False, blank=False, default=False)

    pk = models.CompositePrimaryKey("domain", "legacy")

    @classmethod
    def for_domain(cls, domain, legacy=False):
        """
        Find or create a greenweb badge for a given domain name
        """
        obj, _created = cls.objects.get_or_create(domain = domain, legacy = legacy)
        return obj

    @classmethod
    def clear_cache(cls, domain):
        """
        Clear any existing cached badges for a given domain name
        """
        objects = cls.objects.filter(domain=domain).all()
        for obj in objects:
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

        if self.legacy:
            generator = GreencheckImageV2
        else:
            generator = GreencheckImageV3

        image = generator.generate_greencheck_image(
                self.domain, sitecheck.green, hosting_provider_name
        )

        self.save_image_file(image)

    @property
    def url(self):
        """
        Returns an absolute, publicly accessible URL to this badge
        """
        return default_storage.url(self.path)

    @property
    def version(self):
        if self.legacy:
            return "v2"
        else:
            return "v3"

    def path_for_domain(self):
        """
        The path at which the image will be saved. Note that we explicitly persist this
        in the database rather than deriving from the domain name at runtime, as this gives us
        backwards compatibility. If we weren't to do this, then future changes to the
        format of the path in the code would break existing images.
        """
        return f"greenweb_badges/{self.version}/{self.domain}.png"

@receiver(models.signals.pre_save, sender=GreenDomainBadge)
def create_image_file(instance, **_kwargs):
    instance.create_image_file()

@receiver(models.signals.pre_delete, sender=GreenDomainBadge)
def delete_image_file(instance, **_kwargs):
    instance.delete_image_file()

