# Generated by Django 3.2.18 on 2023-03-07 14:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0044_provider_request_evidence_upload_location'),
    ]

    operations = [
        migrations.AlterField(
            model_name='providerrequestevidence',
            name='public',
            field=models.BooleanField(default=False),
        ),
    ]
