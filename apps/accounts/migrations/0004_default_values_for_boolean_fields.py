# Generated by Django 2.2.7 on 2019-11-04 12:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_index_on_name_for_hp_and_dc"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="credentials_expired",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="user",
            name="enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name="user",
            name="expired",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="user",
            name="locked",
            field=models.BooleanField(default=False),
        ),
    ]
