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

    # Idempotency: skip providers that already have locations.
    providers_with_locations = set(
        HostingProviderLocation.objects.values_list("hostingprovider_id", flat=True)
    )

    # Find the latest ProviderRequest for each provider in two queries, not N.
    latest_pr_by_provider = {}
    for pr in (
        ProviderRequest.objects.exclude(provider=None)
        .order_by("provider_id", "-id")
        .values("id", "provider_id")
    ):
        if pr["provider_id"] not in latest_pr_by_provider:
            latest_pr_by_provider[pr["provider_id"]] = pr["id"]

    # Fetch all locations for those requests in one query.
    pr_location_map = {}
    for loc in ProviderRequestLocation.objects.filter(
        request_id__in=latest_pr_by_provider.values()
    ).order_by("id"):
        pr_location_map.setdefault(loc.request_id, []).append(loc)

    to_create = []
    for hp in Hostingprovider.objects.all().iterator():
        if hp.id in providers_with_locations:
            continue

        pr_id = latest_pr_by_provider.get(hp.id)
        if pr_id:
            pr_locations = pr_location_map.get(pr_id, [])
            for i, loc in enumerate(pr_locations):
                to_create.append(
                    HostingProviderLocation(
                        hostingprovider=hp,
                        name=loc.name,
                        city=loc.city,
                        country=loc.country,
                        is_primary=(i == 0),
                    )
                )
        elif hp.country or hp.city:
            # Legacy provider with no request — use flat country/city
            to_create.append(
                HostingProviderLocation(
                    hostingprovider=hp,
                    city=hp.city or "",
                    country=hp.country,
                    is_primary=True,
                )
            )

    HostingProviderLocation.objects.bulk_create(to_create, batch_size=1000)


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
