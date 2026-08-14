"""Backfill HostingProviderLocation for existing approved providers.

For each Hostingprovider that has an associated ProviderRequest, copy the
ProviderRequestLocation rows into HostingProviderLocation rows, marking the
first as is_primary=True. For providers with no ProviderRequest (legacy data),
create a single HostingProviderLocation from the flat country/city fields.
"""

from django.db import migrations


def backfill_hosting_provider_locations(apps, schema_editor):
    Hostingprovider = apps.get_model("accounts", "Hostingprovider")
    ProviderRequest = apps.get_model("accounts", "ProviderRequest")
    ProviderRequestLocation = apps.get_model("accounts", "ProviderRequestLocation")
    HostingProviderLocation = apps.get_model("accounts", "HostingProviderLocation")

    for hp in Hostingprovider.objects.all():
        # Skip if already has locations (idempotency)
        if HostingProviderLocation.objects.filter(hostingprovider=hp).exists():
            continue

        # Try to find a ProviderRequest linked to this provider (directly or via
        # being the provider that was approved from it)
        pr = ProviderRequest.objects.filter(provider=hp).order_by("-id").first()

        if pr:
            pr_locations = list(
                ProviderRequestLocation.objects.filter(request=pr).order_by("id")
            )
            for i, loc in enumerate(pr_locations):
                HostingProviderLocation.objects.create(
                    hostingprovider=hp,
                    name=loc.name,
                    city=loc.city,
                    country=loc.country,
                    is_primary=(i == 0),
                )
        else:
            # Legacy provider with no request — use flat country/city
            if hp.country or hp.city:
                HostingProviderLocation.objects.create(
                    hostingprovider=hp,
                    city=hp.city or "",
                    country=hp.country,
                    is_primary=True,
                )


def remove_hosting_provider_locations(apps, schema_editor):
    HostingProviderLocation = apps.get_model("accounts", "HostingProviderLocation")
    HostingProviderLocation.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0114_hostingproviderlocation_and_more"),
    ]

    operations = [
        migrations.RunPython(
            backfill_hosting_provider_locations,
            remove_hosting_provider_locations,
        ),
    ]
