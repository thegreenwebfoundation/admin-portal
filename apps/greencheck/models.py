from django.db import models
from django_unixdatetimefield import UnixDateTimeField
from django_mysql.models import EnumField

from apps.accounts.models import Hostingprovider
from .choices import GreenlistChoice, CheckedOptions, BoolChoice

"""
- greencheck_linked - the purpose of the table is not very clear. Contains many entries though.
- greencheck_stats_total and greencheck_stats - self explanatory. Contained in this view here: https://admin.thegreenwebfoundation.org/admin/stats/greencheck

# wait for reply on these.
- greenenergy - also an old table
"""

"""
mysql> show columns from greencheck;
+---------------+--------------------------------------+------+-----+-------------------+----------------+
| Field         | Type                                 | Null | Key | Default           | Extra          |
+---------------+--------------------------------------+------+-----+-------------------+----------------+
| id            | bigint(20)                           | NO   | PRI | NULL              | auto_increment |
| id_hp         | int(11)                              | NO   | MUL | NULL              |                |
| id_greencheck | int(11)                              | NO   |     | 0                 |                |
| type          | enum('url','whois','ip','none','as') | NO   |     | none              |                |
| url           | varchar(255)                         | NO   | MUL | NULL              |                |
| ip            | decimal(39,0)                        | NO   |     | NULL              |                |
| datum         | timestamp                            | NO   | MUL | CURRENT_TIMESTAMP |                |
| green         | enum('yes','no','old')               | NO   | MUL | no                |                |
| tld           | varchar(64)                          | NO   | MUL | NULL              |                |
"""


class Greencheck(models.Model):
    hostingprovider = models.ForeignKey(
        Hostingprovider, db_column='id_hp', on_delete=models.CASCADE
    )
    # missing id_greencheck. Find out what it is first
    date = UnixDateTimeField(db_column='datum')
    green = EnumField(choices=BoolChoice.choices)
    ip = models.IntegerField()
    tld = models.CharField(max_length=64)
    type = EnumField(choices=GreenlistChoice.choices)
    url = models.CharField(max_length=255)

    class Meta:
        db_table = 'greencheck'


class GreencheckIp(models.Model):
    active = models.BooleanField(null=True)
    ip_end = models.IntegerField(db_column='ip_eind')
    ip_start = models.IntegerField()
    hostingprovider = models.ForeignKey(
        Hostingprovider, db_column='id_hp', on_delete=models.CASCADE
    )

    class Meta:
        # managed = False
        db_table = 'greencheck_ip'
        indexes = [
            models.Index(fields=['ip_end']),
            models.Index(fields=['ip_start']),
            models.Index(fields=['active']),
        ]


class GreencheckIpApprove(models.Model):
    action = models.TextField()
    hostingprovider = models.ForeignKey(
        Hostingprovider, on_delete=models.CASCADE,
        db_column='id_hp', null=True
    )
    idorig = models.IntegerField()
    ip_end = models.IntegerField(db_column='ip_eind')
    ip_start = models.IntegerField()
    status = models.TextField()

    class Meta:
        db_table = 'greencheck_ip_approve'
        # managed = False


class GreencheckLinked(models.Model):
    # waiting for use case first...
    pass


class GreenList(models.Model):
    greencheck = models.ForeignKey(
        Greencheck, on_delete=models.CASCADE, db_column='id_greencheck'
    )
    hostingprovider = models.ForeignKey(
        Hostingprovider, on_delete=models.CASCADE, db_column='id_hp'
    )
    last_checked = UnixDateTimeField()
    name = models.CharField(max_length=255, db_column='naam')
    type = EnumField(choices=GreenlistChoice.choices)
    url = models.CharField(max_length=255)
    website = models.CharField(max_length=255)

    class Meta:
        # managed = False
        db_table = 'greenlist'
        indexes = [
            models.Index(fields=['url']),
        ]


# class Tld(models.Model):
#     # wait for confirmation
#     pass


# class MaxmindAsn(models.Model):
#     # wait for confirmation
#     pass


# STATS and stuff


class Stats(models.Model):
    checked_through = EnumField(choices=CheckedOptions.choices)
    count = models.IntegerField()
    ips = models.IntegerField()

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['checked_through']),
        ]


class GreencheckStats(Stats):

    class Meta:
        # managed = False
        db_table = 'greencheck_stats'


class GreencheckStatsTotal(Stats):

    class Meta:
        # managed = False
        db_table = 'greencheck_stats_total'


class GreencheckWeeklyStats(models.Model):
    checks_green = models.IntegerField()
    checks_grey = models.IntegerField()
    checks_perc = models.FloatField()
    checks_total = models.IntegerField()

    monday = models.DateField(db_column='maandag')
    url_green = models.IntegerField()
    url_grey = models.IntegerField()
    url_perc = models.FloatField()
    week = models.IntegerField()
    year = models.PositiveSmallIntegerField()

    class Meta:
        # managed = False
        db_table = 'greencheck_weekly'
