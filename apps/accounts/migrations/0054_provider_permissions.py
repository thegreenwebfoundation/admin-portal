# Generated by Django 3.2.19 on 2023-05-23 15:28

from django.db import migrations
from .. import permissions


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0053_alter_providerrequest_status"),
        ("guardian", "__latest__"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="datacenter",
            options={"permissions": (permissions.manage_datacenter.astuple(),)},
        ),
        migrations.AlterModelOptions(
            name="hostingprovider",
            options={
                "permissions": (permissions.manage_provider.astuple(),),
                "verbose_name": "Hosting Provider",
            },
        ),
    ]
