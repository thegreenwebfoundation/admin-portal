# Generated by Django 2.2.6 on 2019-11-04 08:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_add_django_user_fields"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="datacenter",
            index=models.Index(fields=["name"], name="name"),
        ),
        migrations.AddIndex(
            model_name="hostingprovider",
            index=models.Index(fields=["name"], name="name"),
        ),
    ]
