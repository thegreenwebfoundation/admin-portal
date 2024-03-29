# Generated by Django 2.2.17 on 2021-01-20 14:33

from django.db import migrations, models
import django_mysql.models


class Migration(migrations.Migration):

    dependencies = [
        ("greencheck", "0011_auto_20210120_1418"),
    ]

    operations = [
        migrations.AlterField(
            model_name="greencheck",
            name="greencheck_ip",
            field=models.IntegerField(db_column="id_greencheck", default=0),
        ),
        migrations.AlterField(
            model_name="greencheck",
            name="hostingprovider",
            field=models.IntegerField(db_column="id_hp", default=0),
        ),
        migrations.AlterField(
            model_name="greencheck",
            name="type",
            field=django_mysql.models.EnumField(
                choices=[
                    ("as", "asn"),
                    ("ip", "ip"),
                    ("none", "none"),
                    ("url", "url"),
                    ("whois", "whois"),
                ],
                default="none",
            ),
        ),
        migrations.AlterField(
            model_name="greenlist",
            name="last_checked",
            field=models.DateTimeField(),
        ),
    ]
