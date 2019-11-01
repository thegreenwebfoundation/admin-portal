import ipaddress

from django.db import models
from django_unixdatetimefield import UnixDateTimeField
from django_mysql.models import EnumField

from apps.accounts.models import Hostingprovider
from .choices import (
    ActionChoice,
    GreenlistChoice,
    CheckedOptions,
    BoolChoice,
    StatusApproval,
)

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

    def __str__(self):
        start = ipaddress.ip_address(self.ip_start)
        end = ipaddress.ip_address(self.ip_end)
        return f'{start} - {end}'

    class Meta:
        # managed = False
        db_table = 'greencheck_ip'
        indexes = [
            models.Index(fields=['ip_end'], name='ip_eind'),
            models.Index(fields=['ip_start'], name='ip_start'),
            models.Index(fields=['active'], name='active'),
        ]


class GreencheckIpApprove(models.Model):
    action = models.TextField(choices=ActionChoice.choices)
    hostingprovider = models.ForeignKey(
        Hostingprovider, on_delete=models.CASCADE,
        db_column='id_hp', null=True
    )
    greencheck_ip = models.ForeignKey(
        GreencheckIp, on_delete=models.CASCADE, db_column='idorig', null=True
    )
    ip_end = models.IntegerField(db_column='ip_eind')
    ip_start = models.IntegerField()
    status = models.TextField(choices=StatusApproval.choices)

    def __str__(self):
        start = ipaddress.ip_address(self.ip_start)
        end = ipaddress.ip_address(self.ip_end)
        return f'{start} - {end}: {self.status}'

    class Meta:
        db_table = 'greencheck_ip_approve'
        # managed = False

    def __str__(self):
        return f'Status: {self.status} Action: {self.action}'


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
            models.Index(fields=['url'], name='url'),
        ]


class GreencheckTLD(models.Model):
    checked_domains = models.IntegerField()
    green_domains = models.IntegerField()
    hps = models.IntegerField(verbose_name='Hostingproviders registered in tld')
    tld = models.CharField(max_length=50)
    toplevel = models.CharField(max_length=64)

    class Meta:
        db_table = 'greencheck_tld'
        indexes = [
            models.Index(fields=['tld'], name='tld'),
        ]


class GreencheckASN(models.Model):
    active = models.BooleanField(null=True)
    # https://en.wikipedia.org/wiki/Autonomous_system_(Internet)
    asn = models.IntegerField(verbose_name='Autonomous system number')
    hostingprovider = models.ForeignKey(
        Hostingprovider, on_delete=models.CASCADE
    )

    class Meta:
        db_table = 'greencheck_as'
        indexes = [
            models.Index(fields=['active'], name='active'),
            models.Index(fields=['asn'], name='asn'),
        ]


class GreencheckASNapprove(models.Model):
    action = models.TextField(choices=ActionChoice.choices)
    asn = models.IntegerField()
    hostingprovider = models.ForeignKey(
        Hostingprovider, on_delete=models.CASCADE
    )
    greencheck_asn = models.ForeignKey(
        GreencheckASN, on_delete=models.CASCADE, db_column='idorig', null=True
    )
    status = models.TextField(choices=StatusApproval.choices)

    class Meta:
        db_table = 'greencheck_as_approve'

    def __str__(self):
        return f'Status: {self.status} Action: {self.action}'


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


class GreencheckStats(Stats):

    class Meta:
        # managed = False
        db_table = 'greencheck_stats'
        indexes = [
            models.Index(fields=['checked_through'], name='checked_through'),
        ]


class GreencheckStatsTotal(Stats):

    class Meta:
        # managed = False
        db_table = 'greencheck_stats_total'
        indexes = [
            models.Index(fields=['checked_through'], name='checked_through'),
        ]


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
