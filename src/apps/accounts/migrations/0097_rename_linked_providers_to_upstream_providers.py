# Generated manually on 2026-05-30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0096_create_linked_providers_flag"),
    ]

    operations = [
        # Rename the M2M fields to preserve existing through-table data
        migrations.RenameField(
            model_name="hostingprovider",
            old_name="linked_providers",
            new_name="upstream_providers",
        ),
        migrations.RenameField(
            model_name="providerrequest",
            old_name="linked_providers",
            new_name="upstream_providers",
        ),
        # Update related_name on Hostingprovider.upstream_providers
        migrations.AlterField(
            model_name="hostingprovider",
            name="upstream_providers",
            field=models.ManyToManyField(
                blank=True,
                help_text="Other active verified providers this provider relies on for its green status.",
                related_name="downstream_providers",
                to="accounts.hostingprovider",
                verbose_name="Upstream providers",
            ),
        ),
        # Update related_name on ProviderRequest.upstream_providers
        migrations.AlterField(
            model_name="providerrequest",
            name="upstream_providers",
            field=models.ManyToManyField(
                blank=True,
                help_text="Active verified providers this request relies on for its green status.",
                related_name="downstream_provider_requests",
                to="accounts.hostingprovider",
                verbose_name="Upstream providers",
            ),
        ),
    ]
