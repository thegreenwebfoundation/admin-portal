import pytest
import factory

from django.db.models import signals
from PIL import Image
from unittest import mock

from apps.greencheck.models.green_domain_badge import GreenDomainBadge

@pytest.mark.django_db
class TestGreenDomainBadge():
    @mock.patch("apps.greencheck.models.green_domain_badge.default_storage")
    @mock.patch("apps.greencheck.models.green_domain_badge.GreenDomainChecker")
    @mock.patch("apps.greencheck.models.green_domain_badge.GreencheckImageV3")
    def test_caches_badge(self,
            green_check_image_mock, green_domain_checker_mock, default_storage_mock,
            site_check_factory, hosting_provider_factory
    ):
        """
        GIVEN a domain,
        WHEN I request the green domain badge for the first time,
        THEN A new badge is created and cached.
        """
        domain = "example.com"
        provider_name = "Green Hosting"
        hosting_provider = hosting_provider_factory(name=provider_name)
        sitecheck = site_check_factory(url=domain, green=True, hosting_provider_id=hosting_provider.id)
        green_domain_checker_mock.return_value.check_domain.return_value = sitecheck
        image = mock.MagicMock(spec=Image.Image)
        green_check_image_mock.generate_greencheck_image.return_value = image

        count_before = GreenDomainBadge.objects.count()
        badge = GreenDomainBadge.for_domain(domain)
        count_after = GreenDomainBadge.objects.count()

        assert badge.domain == domain
        assert count_after == count_before + 1

        green_domain_checker_mock.return_value.check_domain.assert_called_with(domain)
        green_check_image_mock.generate_greencheck_image.assert_called_with(domain, True, provider_name)
        default_storage_mock.save.assert_called()

    @mock.patch("apps.greencheck.models.green_domain_badge.default_storage")
    @mock.patch("apps.greencheck.models.green_domain_badge.GreenDomainChecker")
    @mock.patch("apps.greencheck.models.green_domain_badge.GreencheckImageV3")
    def test_uses_cached_badge(self,
            green_check_image_mock, green_domain_checker_mock, default_storage_mock,
            green_domain_badge_factory,
        ):
        """
        GIVEN a domain with a green result,
        WHEN I request an already existing badge,
        THEN A new badge is not created.
        """
        domain = "example.com"

        existing_badge = green_domain_badge_factory(domain=domain)


        count_before = GreenDomainBadge.objects.count()
        new_badge = GreenDomainBadge.for_domain(domain)
        count_after = GreenDomainBadge.objects.count()

        assert existing_badge == new_badge
        assert count_before == count_after
        assert new_badge.domain == domain

        green_domain_checker_mock.return_value.check_domain.assert_not_called()
        green_check_image_mock.generate_greencheck_image.assert_not_called()
        default_storage_mock.save.assert_not_called()


    @mock.patch("apps.greencheck.models.green_domain_badge.default_storage")
    def test_clearing_cache_deletes_cache_entry(self,
        default_storage_mock, green_domain_badge_factory
    ):
        """
        GIVEN an existing green domain badge for a domain,
        WHEN I clear the cache for that domain,
        THEN the cached badge is deleted.
        """
        domain = "example.com"

        badge = green_domain_badge_factory(domain=domain)

        count_before = GreenDomainBadge.objects.count()
        GreenDomainBadge.clear_cache(domain)
        count_after = GreenDomainBadge.objects.count()

        assert count_after == count_before - 1
        default_storage_mock.delete.assert_called_with(badge.path)

    @mock.patch("apps.greencheck.models.green_domain_badge.default_storage")
    def test_url_property_returns_default_storage_url(self,
        default_storage_mock, green_domain_badge_factory
    ):
        """
        GIVEN an existing green domain badge for a domain,
        WHEN I request the badge's URL,
        THEN the default storage url for the corresponding image is returned
        """
        domain = "example.com"

        badge = green_domain_badge_factory(domain=domain)

        url = "https://example.com/example.com.png"

        default_storage_mock.url.return_value = url

        assert badge.url == url
        default_storage_mock.url.assert_called_with(badge.path)




