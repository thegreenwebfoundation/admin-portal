# Generated by Django 3.2.16 on 2022-11-24 20:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0032_providerrequest"),
    ]

    operations = [
        migrations.DeleteModel(
            name="ProviderRequestSupplier",
        ),
    ]