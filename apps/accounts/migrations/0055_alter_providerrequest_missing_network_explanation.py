# Generated by Django 3.2.18 on 2023-06-22 15:53

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0054_providerrequest_network_import_required"),
    ]

    operations = [
        migrations.AlterField(
            model_name="providerrequest",
            name="missing_network_explanation",
            field=models.TextField(
                blank=True,
                help_text="If an organisation is not listing IP Ranges and AS numbers, we need a way to identify them in network lookups.",
                verbose_name="Reason for no IP / AS data",
            ),
        ),
    ]
