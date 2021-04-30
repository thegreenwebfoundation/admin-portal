# Generated by Django 3.2 on 2021-04-29 13:33

import datetime
import django.core.serializers.json
from django.db import migrations, models
import django.utils.timezone
import django_mysql.models
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ("greencheck", "0016_auto_20210424_1603"),
    ]

    operations = [
        migrations.CreateModel(
            name="DailyStat",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created",
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="created",
                    ),
                ),
                (
                    "modified",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="modified",
                    ),
                ),
                (
                    "stat_date",
                    models.DateField(
                        default=datetime.datetime(2021, 4, 28, 13, 33, 1, 936716),
                        verbose_name="Date for stats",
                    ),
                ),
                ("stat_key", models.CharField(max_length=256, verbose_name="")),
                ("count", models.IntegerField()),
                (
                    "extra_data",
                    models.JSONField(
                        encoder=django.core.serializers.json.DjangoJSONEncoder,
                        verbose_name="",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="dailystat",
            index=models.Index(
                fields=["stat_date", "stat_key"], name="greencheck__stat_da_4c46ae_idx"
            ),
        ),
    ]
