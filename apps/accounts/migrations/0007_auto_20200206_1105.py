# Generated by Django 2.2.9 on 2020-02-06 11:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_auto_20191114_1548"),
    ]

    operations = [
        migrations.AlterField(
            model_name="datacenter",
            name="showonwebsite",
            field=models.BooleanField(default=False, verbose_name="Show on website"),
        ),
    ]
