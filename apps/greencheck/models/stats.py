import datetime
import logging
import dramatiq

from typing import List
from dateutil.relativedelta import relativedelta
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext as _
from django_mysql.models import EnumField
from model_utils.models import TimeStampedModel

from .. import choices as gc_choices
from . import checks
from .. import tasks

logger = logging.getLogger(__name__)

now = timezone.now()
yesterday = now - relativedelta(days=1)


class Stats(models.Model):
    checked_through = EnumField(choices=gc_choices.CheckedOptions.choices)
    count = models.IntegerField()
    ips = models.IntegerField()

    class Meta:
        abstract = True


class DailyStatQuerySet(models.QuerySet):
    def daily_stats(self):
        return self.objects.filter(stat_key=gc_choices.DailyStateChoices.DAILY_TOTAL)


class DailyStat(TimeStampedModel):
    """
    Represents the counts of checks for each day
    """

    objects = DailyStatQuerySet.as_manager()

    stat_date = models.DateField(
        _("Date for stats"), auto_now=False, auto_now_add=False, default=yesterday
    )
    # we add this key
    stat_key = models.CharField(_(""), max_length=256)
    count = models.IntegerField()
    green = EnumField(choices=gc_choices.GreenStatChoice.choices, blank=True, null=True)

    # Factories
    @classmethod
    def total_count(cls, date_to_check: datetime.datetime = None):
        """
        Create a total count for the given day
        """

        one_day_ahead = date_to_check + relativedelta(days=1)

        # return all the checks for the day
        qs = checks.Greencheck.objects.filter(
            date__gt=date_to_check.date(), date__lt=one_day_ahead.date()
        )
        # return just the green ones
        green_qs = checks.Greencheck.objects.filter(
            date__gt=date_to_check.date(),
            date__lt=one_day_ahead.date(),
            green=gc_choices.BoolChoice.YES,
        )
        # return just the grey ones
        grey_qs = checks.Greencheck.objects.filter(
            date__gt=date_to_check.date(),
            date__lt=one_day_ahead.date(),
            green=gc_choices.BoolChoice.NO,
        )

        logger.debug(f"date to check: {date_to_check}, qs count: {qs.count()}")
        logger.debug(str(qs.query))

        logger.debug(
            f"date to check: {date_to_check}, green qs count: {grey_qs.count()}"
        )
        logger.debug(str(grey_qs.query))
        logger.debug(
            f"date to check: {date_to_check}, grey qs count: {green_qs.count()}"
        )
        logger.debug(str(green_qs.query))

        mixed_stat = cls(
            count=qs.count(),
            stat_date=date_to_check.date(),
            stat_key=gc_choices.DailyStateChoices.DAILY_TOTAL,
        )
        green_stat = cls(
            count=green_qs.count(),
            stat_date=date_to_check.date(),
            stat_key=gc_choices.DailyStateChoices.DAILY_TOTAL,
            green=gc_choices.BoolChoice.YES,
        )
        grey_stat = cls(
            count=grey_qs.count(),
            stat_date=date_to_check.date(),
            stat_key=gc_choices.DailyStateChoices.DAILY_TOTAL,
            green=gc_choices.BoolChoice.NO,
        )
        stats = [mixed_stat, green_stat, grey_stat]

        # persist to db
        [stat.save() for stat in stats]

        return stats

    @classmethod
    def total_count_for_provider(
        cls, date_to_check: datetime.datetime = None, provider_id: int = None
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

    @classmethod
    def create_counts_for_date_range(cls, date_range, query):
        """
        Accept an iterable of dates, and generate daily stats
        for every date in the iterable
        """
        stats = []

        for date in date_range:
            stat_generation_function = getattr(cls, query)
            stat = stat_generation_function(date)
            stats.append(stat)

        return stats

    @classmethod
    def create_counts_for_date_range_async(
        cls, date_range: List[datetime.datetime], query_name=None
    ):
        """
        Accept an iterable of dates, and add a job to create daily stats
        for every date in the iterable
        """

        deferred_stats = []

        for stat_date in date_range:

            res = tasks.create_stat_async.send(
                date_string=str(stat_date), query_name=query_name
            )
            deferred_stats.append(res)

        logger.debug(deferred_stats)
        return deferred_stats

    # Mutators
    @classmethod
    def clear_counts_for_date_range(
        cls, date_range: List[datetime.datetime] = None, query_name: str = None
    ):
        """
        Accept an iterable of dates, and query_name, then delete all the Daily stats
        matching this combination of dates and query.

        Used to clear out duplicates, before generating new stats.
        """

        date_strings = [str(date_at.date()) for date_at in date_range]
        cls.objects.filter(stat_key=query_name, stat_date__in=date_strings).delete()

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
