# Generated by Django 3.2 on 2021-04-30 10:01

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('greencheck', '0020_auto_20210430_1000'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='dailystat',
            name='extra_data',
        ),
        migrations.AlterField(
            model_name='dailystat',
            name='stat_date',
            field=models.DateField(default=datetime.datetime(2021, 4, 29, 10, 1, 42, 971191), verbose_name='Date for stats'),
        ),
    ]
