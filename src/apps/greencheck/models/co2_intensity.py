from django.db import models

# https://ember-data-api-scg3n.ondigitalocean.app/ember/generation_yearly?_sort=rowid&_facet=year&_facet=variable&country_or_region__exact=World&variable__exact=Fossil&year__exact=2021
GLOBAL_AVG_FOSSIL_SHARE = 61.56

# https://ember-data-api-scg3n.ondigitalocean.app/ember?sql=select+country_or_region%2C+country_code%2C+year%2C+emissions_intensity_gco2_per_kwh%0D%0Afrom+country_overview_yearly%0D%0Awhere+year+%3D+2021%0D%0Aand+country_or_region+%3D+%22World%22%0D%0Aorder+by+country_code+limit+300
GLOBAL_AVG_CO2_INTENSITY = 442.23

class CO2Intensity(models.Model):
    """
    A lookup table for returning carbon intensity figures
    for a given region, used when looking up IPs and/or domains.

    Works at a country level of granularity at present, with the expectation
    that grid or hosting provider data can offer greater detail as available.
    """

    country_name = models.CharField(max_length=255)
    country_code_iso_2 = models.CharField(max_length=255, blank=True, null=True)
    country_code_iso_3 = models.CharField(max_length=255)
    carbon_intensity = models.FloatField()
    # marginal, average or perhaps residual
    carbon_intensity_type = models.CharField(max_length=255)
    generation_from_fossil = models.FloatField(default=0)
    year = models.IntegerField()

    def __str__(self):
        return f"{self.country_name} - {self.year}"

    @classmethod
    def check_for_country_code(cls, country_code):
        """
        Accept 2 letter country code, and return the CO2 Intensity
        figures for the corresponding country if present
        """

        # we try to return the latest value we have for a given country
        # in some places data can be more than a year old, so we allow
        # for this
        res = (
            cls.objects.filter(country_code_iso_2=country_code)
            .order_by("-year")
            .first()
        )

        # do we have a result? return it
        if res:
            return res

        # otherwise fall back to global value
        return cls.global_value()

    @classmethod
    def global_value(cls):
        """
        Return a default lookup value for when we
        do not have enough information to return information
        based on a given country.
        """
        return CO2Intensity(
            country_name="World",
            country_code_iso_2="xx",
            country_code_iso_3="xxx",
            carbon_intensity_type="avg",
            carbon_intensity=GLOBAL_AVG_CO2_INTENSITY,
            generation_from_fossil=GLOBAL_AVG_FOSSIL_SHARE,
            year=2021,
        )
