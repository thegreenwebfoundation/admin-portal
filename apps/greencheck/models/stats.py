import datetime
import logging
from typing import List

from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta
from django.db import connection, models
from django.utils import timezone
from django.utils.translation import gettext as _
from django_mysql.models import EnumField
from model_utils.models import TimeStampedModel

from .. import choices as gc_choices
from .. import tasks
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


class DailyStatQuerySet(models.QuerySet):
    """
    Table level queries for DailyStats
    """

    def daily_stats(self):
        return self.filter(stat_key=gc_choices.DailyStatChoices.DAILY_TOTAL)

    def daily_stats_for_provider(self, provider_id: int = None):
        """
        Return all the daily counts for a given provider
        """
        daily_total = gc_choices.DailyStatChoices.DAILY_TOTAL

        # exit early if no provider
        if not provider_id:
            domain_key = f"{daily_total}:provider"
            return self.filter(stat_key__icontains=domain_key)

        # otherwise be more
        provider_key = f"{daily_total}:provider:{provider_id}"
        return self.filter(stat_key=provider_key)

    def daily_stats_for_domain(self, domain: str = None):
        """
        Return all the daily counts for a given domain
        """

        # validate domain

        daily_total = gc_choices.DailyStatChoices.DAILY_TOTAL

        # return early if we're not filtering to specific domain
        if not domain:
            domain_key = f"{daily_total}:domain"
            return self.filter(stat_key__icontains=domain_key)

        # otherwise use the domain too
        domain_key = f"{daily_total}:domain:{domain}"
        return self.filter(stat_key=domain_key)


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

        logger.info(f"Generating stats for {date_to_check.date()}")

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
            stat_key=gc_choices.DailyStatChoices.DAILY_TOTAL,
        )
        green_stat = cls(
            count=green_qs.count(),
            stat_date=date_to_check.date(),
            stat_key=gc_choices.DailyStatChoices.DAILY_TOTAL,
            green=gc_choices.BoolChoice.YES,
        )
        grey_stat = cls(
            count=grey_qs.count(),
            stat_date=date_to_check.date(),
            stat_key=gc_choices.DailyStatChoices.DAILY_TOTAL,
            green=gc_choices.BoolChoice.NO,
        )
        stats = [mixed_stat, green_stat, grey_stat]

        # persist to db
        [stat.save() for stat in stats]
        logger.info(f"Saved stats: {mixed_stat}, {green_stat}, {grey_stat}")

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
            stat_key=f"{gc_choices.DailyStatChoices.DAILY_TOTAL}:provider:{provider_id}",
        )

        green_stat = cls(
            count=green_qs.count(),
            stat_date=date_to_check.date(),
            green=gc_choices.BoolChoice.YES,
            stat_key=f"{gc_choices.DailyStatChoices.DAILY_TOTAL}:provider:{provider_id}",
        )
        grey_stat = cls(
            count=grey_qs.count(),
            stat_date=date_to_check.date(),
            stat_key=f"{gc_choices.DailyStatChoices.DAILY_TOTAL}:provider:{provider_id}",
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

        for stat_datetime in date_range:

            res = tasks.create_stat_async.send(
                date_string=str(stat_datetime.date()), query_name=query_name
            )
            deferred_stats.append(res)

        logger.debug(deferred_stats)
        return deferred_stats

    @classmethod
    def create_top_domains_for_day(
        cls, chosen_date: str = None, green: str = gc_choices.GreenStatChoice.YES
    ):
        """
        Create a top N listing of domains grouped by count, and ordered
        by number of checks, for the dates given.
        We drop down to raw SQL to generate this, because the greencheck
        table is some integrity issues that prevent us from using
        foreign keys.
        """
        from .checks import Greencheck

        greencheck_table = Greencheck._meta.db_table

        logger.info(f"provided chosen date: {chosen_date}")

        date_start, date_end = cls._single_day_date_range(chosen_date=str(chosen_date))

        logger.info(f"sending these dates: {date_start}, {date_end}")

        results = []
        with connection.cursor() as cursor:
            # passing in greencheck table to execute below, escapes the
            # table name, making mysql crash, so we need to add it like so
            raw_query = (
                "SELECT url , count(id) AS popularity "
                f"FROM {greencheck_table} "
                "WHERE datum BETWEEN %s AND %s "
                "AND green = %s "
                "GROUP BY url "
                "ORDER BY popularity DESC"
            )
            logger.info(raw_query)
            cursor.execute(raw_query, [date_start, date_end, green])

            results = cursor.fetchall()
        logger.info(results)

        for res in results:
            domain, count = res
            daily_total = gc_choices.DailyStatChoices.DAILY_TOTAL
            domain_key = f"{daily_total}:domain:{domain}"

            # save our results as DailyStats
            DailyStat.objects.create(
                count=count,
                green=green,
                stat_key=domain_key,
                stat_date=str(chosen_date),
            )
        return results

    @classmethod
    def create_top_hosting_providers_for_day(
        cls, chosen_date: str = None, green: str = gc_choices.GreenStatChoice.YES
    ):
        """
        Create a top N listing of hosting providers grouped by count, and ordered
        by number of checks, for the dates given.
        We drop down to raw SQL to generate this, because the greencheck
        table is some integrity issues that prevent us from using
        foreign keys.
        """
        from .checks import Greencheck

        greencheck_table = Greencheck._meta.db_table
        logger.info(f"provided chosen date: {chosen_date}")

        date_start, date_end = cls._single_day_date_range(chosen_date=str(chosen_date))

        logger.info(f"sending these dates: {date_start}, {date_end}")

        results = []
        with connection.cursor() as cursor:
            # passing in greencheck table to execute below, escapes the
            # table name, making mysql crash, so we need to add it like so
            raw_query = (
                "SELECT id_hp , count(id) AS popularity "
                f"FROM {greencheck_table} "
                "WHERE datum BETWEEN %s AND %s "
                "AND green = %s "
                "GROUP BY id_hp "
                "ORDER BY popularity DESC"
            )
            cursor.execute(raw_query, [date_start, date_end, green])
            results = cursor.fetchall()

        for res in results:
            hosting_provider_id, count = res
            daily_total = gc_choices.DailyStatChoices.DAILY_TOTAL
            provider_key = f"{daily_total}:provider:{hosting_provider_id}"

            # save our results as DailyStats
            DailyStat.objects.create(
                count=count,
                green=green,
                stat_key=provider_key,
                stat_date=str(chosen_date),
            )
        return results

    @classmethod
    def _single_day_date_range(self, chosen_date: str = None):
        """
        Accept a datestring, and return start and end datestrings
        suitable for using in day calculations
        """
        logger.info(f"chosen date: {chosen_date}")
        if chosen_date is None:
            chosen_date = str(timezone.now().date())

        following_day = date_parser.parse(chosen_date) + relativedelta(days=1)

        return [chosen_date, str(following_day.date())]

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

        date_strings = [str(stat_datetime.date()) for stat_datetime in date_range]
        cls.objects.filter(stat_key=query_name, stat_date__in=date_strings).delete()

    # Queries
    @classmethod
    def stats_by_day_since(cls, start_date=None):
        """
        """
        return (
            cls.objects.daily_stats()
            .filter(stat_date__gte=start_date, green__in=["yes", "no"])
            .order_by("-stat_date")
        )

    @classmethod
    def stats_by_day_(cls, start_date=None):
        return (
            cls.objects.daily_stats()
            .filter(stat_date__gte=start_date, green__in=["yes", "no"])
            .order_by("-stat_date")
        )

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
