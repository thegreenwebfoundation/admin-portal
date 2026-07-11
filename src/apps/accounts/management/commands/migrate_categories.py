from django.core.management.base import BaseCommand
from ...models import Service, Hostingprovider
from taggit import models as tag_models
import typing
import logging

# Our updated canonical list of services
SERVICE_NAMES = [
    ("Compute: Shared Hosting for Websites", "shared-hosting"),
    ("Compute: Virtual Private Servers", "virtual-private-servers"),
    ("Compute: Physical Servers", "physical-servers"),
    ("Compute: Colocation Services", "colocation-services"),
    ("Storage: Object Storage", "object-storage"),
    ("Storage: Block Storage", "block-storage"),
    ("Network: Content Delivery Networks", "content-delivery-network"),
    ("Platform: Platform As A Service", "platform-as-a-service"),
    ("Platform: Managed WordPress Hosting", "managed-wordpress-hosting"),
]

# the mappings we need to migrate them across
MIGRATION_DICT = {
    "shared-hosting": [9, 1],
    "virtual-private-servers": [2],
    "physical-servers": [4],
    "colocation-services": [12],
    "object-storage": [14],
    "block-storage": [15],
    "content-delivery-network": [13],
    "platform-as-a-service": [10, 16],
    "managed-wordpress-hosting": [3],
}

# these services are not migrated across. we just delete them.
# (
# (5, "Consulting"),
# (6, "design"),
# (7, "development"),
# (8, "new-digital-service"),
# (11, "carbon-tracking"),
# (17, "datacenter-design-and-build"),
# (18, "digital-product-design-and-development",)
# (19, "sustainability-strategy-for-digital-services",)
# )
SERVICES_TO_DELETE = [5, 6, 7, 8, 11, 17, 18, 19]

logger = logging.getLogger(__name__)


class ServiceMigrator:
    """
    A class to create the taxonomy of services providers delcare that they offer.
    """

    def create_provider_service_list(self):
        """
        Create our list of services our providers offer, and if they don't aleady exist,
        make sure their names are correct.
        """
        created_service_list = []

        for name, slug in SERVICE_NAMES:
            service, created = Service.objects.get_or_create(slug=slug)
            service.name = name
            service.save()

            if created:
                created_service_list.append(service)

        return created_service_list

    def migrate_service_tags_to_service(
        self, service_slug: str, service_tag_ids: typing.List[int]
    ):
        """
        Accept `service_slug`, the slug to identify a given Service to
        migrate to, and add it to all the providers who already have
        the service_tags identified by `service_tag_ids` a list of
        integers to identify the existing 'legacy' tags in use
        """
        service = Service.objects.get(slug=service_slug)

        for service_tag_id in service_tag_ids:
            service_tag = tag_models.Tag.objects.get(id=service_tag_id)

            # check our count of providers with old tag
            providers_with_matching_tag = Hostingprovider.objects.filter(
                service_tags=service_tag
            )
            # check our count of providers with newer "service"
            providers_with_matching_service = Hostingprovider.objects.filter(
                services=service
            )

            logger.info(
                f"Providers with service tag {service_tag}: "
                f"{providers_with_matching_tag.count()}"
            )
            logger.info(
                f"Providers with service {service}: "
                f"{providers_with_matching_service.count()}"
            )
            logger.info("migrating...")
            # do the actual migration
            for provider in providers_with_matching_tag:
                self.swap_tag(provider, service_tag, service)

            logger.info("migrated")

            logger.info(
                f"Providers with service {service}: "
                f"{Hostingprovider.objects.filter(services=service).count()}"
            )

    def swap_tag(
        self,
        provider: Hostingprovider,
        old_service_tag_to_remove: tag_models.Tag,
        new_service_to_add: Service,
    ):
        """
        Remove the older taggit tag identified by `old_service_tag_to_remove`,
        and replace with the newer service tag, `new_service_to_add`
        """
        provider.service_tags.remove(old_service_tag_to_remove)
        provider.services.add(new_service_to_add)
        provider.save()


class Command(BaseCommand):
    """
    A command to migrate to make sure we have our required set of categories in place.
    Because we make quite a lot of use the ORM, this is a management command, rather
    than a data migration, but it's intended to only be used once.
    """

    help = "Make sure we have our shortlist of service categories from providers"

    def handle(self, *args, **options):
        migrator = ServiceMigrator()
        # make sure we have our new list of services
        created_service_list = migrator.create_provider_service_list()
        self.stdout.write(
            self.style.SUCCESS(
                "Created our updated list of services"
                f"Created {len(created_service_list)} new services"
            )
        )

        # Migrate these services using the appropriate mappings
        for slug in MIGRATION_DICT.keys():
            migrator.migrate_service_tags_to_service(slug, MIGRATION_DICT[slug])

        # remove previous tags
        for service_tag_id in SERVICES_TO_DELETE:
            tag_models.Tag.objects.get(id=service_tag_id).delete()

        self.stdout.write(self.style.SUCCESS("All done!"))
