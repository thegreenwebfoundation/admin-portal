# Generated by Django 2.2.17 on 2021-01-20 11:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("greencheck", "0009_auto_20210120_1029"),
    ]

    operations = [
        migrations.CreateModel(
            name="GreenDomain",
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
                ("url", models.CharField(max_length=255)),
                ("hosted_by", models.CharField(max_length=255)),
                ("hosted_by_website", models.CharField(max_length=255)),
                ("partner", models.CharField(max_length=255)),
                ("green", models.BooleanField()),
                ("hosted_by_id", models.IntegerField()),
                ("modified", models.DateTimeField()),
            ],
            options={
                "db_table": "greendomain",
            },
        ),
        migrations.CreateModel(
            name="TopUrl",
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
                ("url", models.CharField(max_length=255)),
            ],
            options={
                "db_table": "top_1m_urls",
            },
        ),
        migrations.AlterModelTable(
            name="greencheck",
            table="greencheck_2020",
        ),
    ]
