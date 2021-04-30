import datetime
import logging

from dateutil.relativedelta import relativedelta
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext as _
from django_mysql.models import EnumField
from model_utils.models import TimeStampedModel

from .. import choices as gc_choices
from . import checks

logger = logging.getLogger(__name__)

now = timezone.now()
yesterday = now - relativedelta(days=1)


class Stats(models.Model):
    checked_through = EnumField(choices=gc_choices.CheckedOptions.choices)
    count = models.IntegerField()
    ips = models.IntegerField()

    class Meta:
        abstract = True


class DailyStat(TimeStampedModel):
    """
    Represents the counts of checks for each day
    """

    stat_date = models.DateField(
        _("Date for stats"), auto_now=False, auto_now_add=False, default=yesterday
    )
    # we add this key
    stat_key = models.CharField(_(""), max_length=256)
    count = models.IntegerField()
    green = EnumField(
        choices=gc_choices.BoolChoice.choices, default=gc_choices.BoolChoice.NO,
    )

    # Factories

    @classmethod
    def total_count(cls, date_to_check: datetime.date = None):
        """
        Create a total count for the given day
        """
        one_day_ahead = date_to_check + relativedelta(days=1)

        qs = checks.Greencheck.objects.filter(
            date__gt=date_to_check.date(), date__lt=one_day_ahead.date()
        )
        stat = cls(
            count=qs.count(),
            stat_date=date_to_check.date(),
            stat_key=gc_choices.DailyStateChoices.DAILY_TOTAL,
            green=gc_choices.BoolChoice.YES,
        )
        green_stat = cls(
            count=qs.count(),
            stat_date=date_to_check.date(),
            stat_key=gc_choices.DailyStateChoices.DAILY_TOTAL,
            green=gc_choices.BoolChoice.YES,
        )
        grey_stat = cls(
            count=qs.count(),
            stat_date=date_to_check.date(),
            stat_key=gc_choices.DailyStateChoices.DAILY_TOTAL,
            green=gc_choices.BoolChoice.NO,
        )
        stats = [stat, green_stat, grey_stat]

        # persist to db
        [stat.save() for stat in stats]

        return stats

    @classmethod
    def total_count_for_provider(
        cls, date_to_check: datetime.date = None, provider_id: int = None
    ):
        """
        Create a total count for given day for the provider.
        """
        one_day_ahead = date_to_check + relativedelta(days=1)

        qs = checks.Greencheck.objects.filter(
            date__gt=date_to_check.date(),
            date__lt=one_day_ahead.date(),
            hostingprovider=provider_id,
        )

        green_qs = checks.Greencheck.objects.filter(
            date__gt=date_to_check.date(),
            date__lt=one_day_ahead.date(),
            hostingprovider=provider_id,
            green=gc_choices.BoolChoice.YES,
        )
        grey_qs = checks.Greencheck.objects.filter(
            date__gt=date_to_check.date(),
            date__lt=one_day_ahead.date(),
            hostingprovider=provider_id,
            green=gc_choices.BoolChoice.NO,
        )
        stat = cls(
            count=qs.count(),
            stat_date=date_to_check.date(),
            stat_key=f"{gc_choices.DailyStateChoices.DAILY_TOTAL}:provider:{provider_id}",
        )

        green_stat = cls(
            count=green_qs.count(),
            stat_date=date_to_check.date(),
            green=gc_choices.BoolChoice.YES,
            stat_key=f"{gc_choices.DailyStateChoices.DAILY_TOTAL}:provider:{provider_id}",
        )
        grey_stat = cls(
            count=grey_qs.count(),
            stat_date=date_to_check.date(),
            stat_key=f"{gc_choices.DailyStateChoices.DAILY_TOTAL}:provider:{provider_id}",
            green=gc_choices.BoolChoice.NO,
        )

        stats = [stat, green_stat, grey_stat]

        # persist to db
        [stat.save() for stat in stats]

        return stats

    # Mutators
    # Queries

    # Properties

    def __str__(self):
        title = f"{self.stat_key}-{self.stat_date}"

        if self.green == gc_choices.BoolChoice.YES:
            return f"{title}-green"
        elif self.green == gc_choices.BoolChoice.NO:
            return f"{title}-grey"
        return title

    class Meta:
        indexes = [
            models.Index(fields=["stat_date", "stat_key"]),
        ]
