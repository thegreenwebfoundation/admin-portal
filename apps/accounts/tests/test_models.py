from carbon_txt.finders import UnreachableCarbonTxtFile
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from apps.accounts.models.choices import ModelType
from apps.accounts import models as ac_models
from carbon_txt.exceptions import UnreachableCarbonTxtFile
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.core.files import base as dj_files

# TODO these hit the database, when they probably don't need to, and
#  this will make tests slow. If we can test that these objects are
#  valid another way we should - maybe checking at the field level,
#  or form level.

from django.contrib.auth import get_user_model

User = get_user_model()


class TestDatacenter:
    @pytest.mark.parametrize(
        "accounting_model",
        (
            "groeneenergie",
            "mixed",
            "compensatie",
        ),
    )
    def test_accepted_ways_to_model(self, hosting_provider, db, accounting_model):
        val, *_ = [
            choice for choice in ModelType.choices if choice[0] == accounting_model
        ]

        # if we don't have an allowed value this should throw an error
        hosting_provider.model = accounting_model
        hosting_provider.save()

        assert hosting_provider.model == accounting_model


class TestHostingProvider:
    @pytest.mark.parametrize(
        "accounting_model",
        (
            "groeneenergie",
            "mixed",
            "compensatie",
        ),
    )
    @pytest.mark.django_db
    def test_accepted_ways_to_model(
        self, datacenter, sample_hoster_user, accounting_model, hosting_provider
    ):
        hosting_provider.save()

        val, *_ = [
            choice for choice in ModelType.choices if choice[0] == accounting_model
        ]

        # if we don't have an allowed value this should throw an error
        datacenter.model = accounting_model
        datacenter.save()

        assert datacenter.model == accounting_model

    def test_archive(
        self, db, hosting_provider_factory, green_ip_factory, green_asn_factory, green_domain_factory
    ):

        provider = hosting_provider_factory.create()
        # make a green ip range
        ip_range = green_ip_factory.create(hostingprovider=provider)
        # make a green asn range
        as_network = green_asn_factory.create(hostingprovider=provider)
        # make a green domain
        green_domain = green_domain_factory.create(hosted_by_id=provider.id)

        assert ip_range.active is True
        assert as_network.active is True

        provider.archive()
        ip_range.refresh_from_db()
        as_network.refresh_from_db()
        green_domain = green_domain.refresh_from_db()

        assert provider.active_ip_ranges().count() == 0
        assert provider.active_asns().count() == 0
        assert ip_range.active is False
        assert as_network.active is False
        #
        assert provider.archived is True
        assert provider.is_listed is False
        assert not green_domain

    @pytest.mark.django_db
    def test_clear_green_domains_cache_called_when_website_updated(self, db, hosting_provider_factory, mocker):
        clear_cached_greendomains = mocker.patch("apps.accounts.models.Hostingprovider._clear_cached_greendomains")
        provider = hosting_provider_factory.create()
        provider.save()
        provider.website = "https://newwebsite.com"
        provider.save()
        assert clear_cached_greendomains.call_count == 2

    @pytest.mark.django_db
    def test_clear_green_domains_cache_called_when_is_listed_updated(self, db, hosting_provider_factory, mocker):
        clear_cached_greendomains = mocker.patch("apps.accounts.models.Hostingprovider._clear_cached_greendomains")
        provider = hosting_provider_factory.create()
        provider.save()
        provider.is_listed = not provider.is_listed
        provider.save()
        assert clear_cached_greendomains.call_count == 2

    @pytest.mark.django_db
    def test_clear_green_domains_cache_called_when_name_updated(self, db, hosting_provider_factory, mocker):
        clear_cached_greendomains = mocker.patch("apps.accounts.models.Hostingprovider._clear_cached_greendomains")
        provider = hosting_provider_factory.create()
        provider.save()
        provider.name = "New rebranded hosting provider!"
        provider.save()
        assert clear_cached_greendomains.call_count == 2

    @pytest.mark.django_db
    def test_clear_green_domains_cache_called_when_other_field_updated(self, db, hosting_provider_factory, mocker):
        clear_cached_greendomains = mocker.patch("apps.accounts.models.Hostingprovider._clear_cached_greendomains")
        provider = hosting_provider_factory.create()
        provider.save()
        provider.description = "a new description"

    @pytest.mark.django_db
    def test_last_open_request_with_no_request(self, db, hosting_provider_factory):
        """
        Given a provider with no open requests
        When I get the last open request for the provider
        It should return None.
        """
        provider = hosting_provider_factory.create()
        provider.save()
        assert provider.last_open_request is None

    @pytest.mark.django_db
    def test_last_open_request_with_open_request(self, db, hosting_provider_factory, provider_request_factory):
        """
        Given a provider with a single open request
        When I get the last open request for the provider
        It should return the request
        """
        provider = hosting_provider_factory.create()
        provider.save()
        request = provider_request_factory(
            provider = provider,
            status = ac_models.ProviderRequestStatus.OPEN
        )
        request.save()
        assert provider.last_open_request == request

    @pytest.mark.django_db
    def test_last_open_request_with_pending_request(self, db, hosting_provider_factory, provider_request_factory):
        """
        Given a provider with a single pending request
        When I get the last open request for the provider
        It should return the request
        """
        provider = hosting_provider_factory.create()
        provider.save()
        request = provider_request_factory(
            provider = provider,
            status = ac_models.ProviderRequestStatus.PENDING_REVIEW
        )
        request.save()
        assert provider.last_open_request == request

    @pytest.mark.django_db
    def test_last_open_request_with_non_open_request(self, db, hosting_provider_factory, provider_request_factory):
        """
        Given a provider with a single non-open and non-pending request
        When I get the last open request for the provider
        It should return None
        """
        provider = hosting_provider_factory.create()
        provider.save()
        request = provider_request_factory(
            provider = provider,
            status = ac_models.ProviderRequestStatus.APPROVED
        )
        request.save()
        assert provider.last_open_request is None

    @pytest.mark.django_db
    def test_last_open_request_with_two_open_requests(self, db, hosting_provider_factory, provider_request_factory):
        """
        Given a provider with two non-open request
        When I get the last open request for the provider
        It should return the most recent of thethe most recent of the two.
        """
        provider = hosting_provider_factory.create()
        provider.save()
        request1 = provider_request_factory(
            provider = provider,
            status = ac_models.ProviderRequestStatus.OPEN,
            modified = timezone.now() - relativedelta(days=-1)
        )
        request1.save()
        request2 = provider_request_factory(
            provider = provider,
            status = ac_models.ProviderRequestStatus.OPEN,
            modified = timezone.now()
        )
        request2.save()
        assert provider.last_open_request == request2

class TestHostingProviderEvidence:
    """
    Tests to check that we save files with scaleway
    """

    @pytest.mark.smoke_test
    def test_upload_hosting_evidence(self, db, sample_hoster_user, hosting_provider):
        """
        This exercises the API, so we can check that working with files
        when we use the object storage for file attachments instead of the
        server file system behaves as expected
        """

        now = timezone.now()
        one_year_from_now = now + relativedelta(years=1)

        evidence = ac_models.HostingProviderSupportingDocument(
            valid_from=now,
            valid_to=one_year_from_now,
            description="some description",
            title="Title",
            public=True,
        )
        evidence.save()
        hosting_provider.save()
        hosting_provider.hostingprovider_evidence.add(evidence)

        attachment_contents = b"text-content"
        evidence.attachment.save(
            "django_test.txt", dj_files.ContentFile(attachment_contents)
        )

        # can we read the file again?
        assert evidence.attachment.read() == attachment_contents


class TestUser:
    def test_create_user_has_password_and_legacy_password_set(
        self, db, hosting_provider
    ):
        """
        Test that when we create a user, we set both passwords, so we
        don't cause an unfortunate integrity error.

        NOTE: Once we stop using the old admin, this might no be needed
        """
        hosting_provider.save()

        new_user = User(
            username="keen_user",
            password="topSekrit",
            email="email@example.com",
        )

        new_user.save()
        # check that we have the correct columns updated

        # is the password set?
        assert new_user.legacy_password
        # and is it the same as the actual password we use
        # for logging in via django?
        assert new_user.legacy_password == new_user.password


class TestProviderCarbonTxt:
    @pytest.mark.django_db
    def test_state_pending_validation(self, provider_carbon_txt_factory):
        """
        A ProviderCarbonTxt without a carbon_txt_url is in the pending validation state,
        and is not valid.
        """

        carbon_txt = provider_carbon_txt_factory(
            domain = "example.com",
            carbon_txt_url = None,
            is_delegation_set = False,
        )

        assert carbon_txt.state == ac_models.ProviderCarbonTxt.State.PENDING_VALIDATION
        assert not carbon_txt.is_valid

    @pytest.mark.django_db
    def test_state_pending_delegation(self, provider_carbon_txt_factory):
        """
        A ProviderCarbonTxt with a carbon_txt_url, but without the is_delegation_set
        flag set is in the pending delegation state, and is valid.
        """

        carbon_txt = provider_carbon_txt_factory(
            domain = "example.com",
            carbon_txt_url = "https://example.com/carbon.txt",
            is_delegation_set = False,
        )

        assert carbon_txt.state == ac_models.ProviderCarbonTxt.State.PENDING_DELEGATION
        assert carbon_txt.is_valid

    @pytest.mark.django_db
    def test_state_active(self, provider_carbon_txt_factory):
        """
        A ProviderCarbonTxt with a carbon_txt_url, and the is_delegation_set
        flag set is in the active state, and is valid.
        """

        carbon_txt = provider_carbon_txt_factory(
            domain = "example.com",
            carbon_txt_url = "https://example.com/carbon.txt",
            is_delegation_set = True,
        )

        assert carbon_txt.state == ac_models.ProviderCarbonTxt.State.ACTIVE
        assert carbon_txt.is_valid

    @pytest.mark.django_db
    def test_validate_without_domain(self):
        """
        Validating a ProviderCarbonTxt wtihout a domain raises an error.
        """
        # Given a carbon_txt with no domain set
        carbon_txt = ac_models.ProviderCarbonTxt()

        # When I attempt to validate
        # Then an error should be raised.
        with pytest.raises(ac_models.ProviderCarbonTxt.BlankDomainError):
            carbon_txt.validate()

    @pytest.mark.django_db
    @patch("apps.accounts.models.hosting.carbon_txt.CarbonTxtValidator")
    def test_validate_with_invalid_carbon_txt(self, validator_factory_mock, provider_carbon_txt_factory):
        """
        Validating a ProviderCarbonTxt for a domain with an invalid carbon.txt
        raises an error.
        """
        # Given a carbon_txt with a domain set, and a carbon.txt with errors
        carbon_txt = provider_carbon_txt_factory(
            domain = "example.com",
            carbon_txt_url = None,
            is_delegation_set = False
        )

        validation_result = MagicMock()
        validation_result.result = None
        validation_result.url = None
        validation_result.exceptions = ["An exception raised while validating the carbon.txt"]
        validator = validator_factory_mock.return_value
        validator.validate_domain.return_value = validation_result

        # When I attempt to validate
        # Then an error should be raised.
        with pytest.raises(ac_models.ProviderCarbonTxt.CarbonTxtNotValidatedError):
            carbon_txt.validate()

    @pytest.mark.django_db
    @patch("apps.accounts.models.hosting.carbon_txt.CarbonTxtValidator")
    def test_validate_with_valid_carbon_txt(self, validator_factory_mock, provider_carbon_txt_factory):
        """
        Validating a ProviderCarbonTxt for a domain with a valid carbon txt
        sets the carbon_txt_url
        """
        # Given a carbon_txt with a domain set, and a carbon.txt without errors
        carbon_txt = provider_carbon_txt_factory(
            domain = "example.com",
            carbon_txt_url = None,
            is_delegation_set = False
        )

        validation_result = MagicMock()
        validation_result.exceptions = []
        validation_result.result = MagicMock()
        validation_result.url = "https://examples/.well-known/carbon.txt"

        validator = validator_factory_mock.return_value
        validator.validate_domain.return_value = validation_result

        # When I attempt to validate
        result = carbon_txt.validate()

        # Then "True" should be returned.
        assert result

        # And the carbon_txt_url should be set
        assert carbon_txt.carbon_txt_url == validation_result.url


    @pytest.mark.django_db
    @patch("apps.accounts.models.hosting.carbon_txt.FileFinder")
    def test_find_for_domain_with_carbon_txt_and_existing_provider_carbon_txt(self, finder_factory_mock, provider_carbon_txt_factory):
        """
        Looking up a ProviderCarbonTxt for an existing provider via a domain
        which delegates to it.
        """
        # Given a carbon_txt exists
        carbon_txt = provider_carbon_txt_factory(
            domain = "example.com",
            carbon_txt_url = "https://example.com/carbon.txt",
            is_delegation_set = True
        )

        # When I query a domain which delegates to that carbon.txt
        resolution_result = MagicMock()
        resolution_result.uri =  carbon_txt.carbon_txt_url

        finder = finder_factory_mock.return_value
        finder.resolve_domain.return_value = resolution_result

        result = ac_models.ProviderCarbonTxt.find_for_domain("foobar.com")

        # Then the relevant carbon_txt should be returned.
        assert result == carbon_txt


    @pytest.mark.django_db
    @patch("apps.accounts.models.hosting.carbon_txt.FileFinder")
    def test_find_for_domain_with_carbon_txt_and_no_provider_carbon_txt(self, finder_factory_mock):
        """
        Looking up a ProviderCarbonTxt for a non-existent  provider via a domain
        with a carbon.txt
        """
        # Given a domain with a carbon.txt which is not registered for a provider
        resolution_result = MagicMock()
        resolution_result.uri = "https://foobar.com/carbon.txt"

        finder = finder_factory_mock.return_value
        finder.resolve_domain.return_value = resolution_result


        # When I query that domain
        result = ac_models.ProviderCarbonTxt.find_for_domain("foobar.com")

        # Then no carbon.txt should be returned.
        assert result is None

    @pytest.mark.django_db
    @patch("apps.accounts.models.hosting.carbon_txt.FileFinder")
    def test_find_for_domain_with_no_carbon_txt(self, finder_factory_mock):
        """
        Looking up a ProviderCarbonTxt for a domain with no carbon.txt
        """
        # Given a domain without a carbon.txt

        finder = finder_factory_mock.return_value

        def side_effect(*args, **kwargs):
            raise UnreachableCarbonTxtFile

        finder.resolve_domain.side_effect = side_effect

        # When I query that domain
        result = ac_models.ProviderCarbonTxt.find_for_domain("foobar.com")

        # Then no carbon.txt should be returned.
        assert result is None
