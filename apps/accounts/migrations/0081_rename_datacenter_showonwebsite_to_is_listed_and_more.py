# Generated by Django 5.0.9 on 2025-07-08 03:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0080_rename_showonwebsite_to_is_listed_provider"),
    ]

    operations = [
        migrations.RenameField(
            model_name="datacenter",
            old_name="showonwebsite",
            new_name="is_listed",
        ),
        migrations.AlterField(
            model_name="hostingprovider",
            name="is_listed",
            field=models.BooleanField(
                default=False,
                verbose_name="List this provider in the greenweb directory?",
            ),
        ),
    ]
