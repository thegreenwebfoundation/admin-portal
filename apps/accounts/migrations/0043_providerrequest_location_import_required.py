# Generated by Django 3.2.18 on 2023-02-20 13:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0042_providerrequest_missing_network_explanation'),
    ]

    operations = [
        migrations.AddField(
            model_name='providerrequest',
            name='location_import_required',
            field=models.BooleanField(default=False),
        ),
    ]
