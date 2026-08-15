"""
Tests for the Link Disclosures to Regions feature.

Covers:
- ProviderRequestEvidenceLocation through model
- HostingProviderSupportingDocumentLocation through model
- HostingProviderLocation model (is_primary sync)
- Wizard submission with region_scope='all' and region_scope='specific'
- Wizard submission with the flag off (auto all regions)
- Approval flow: live locations created, region links carried across
"""

import random
from ipaddress import ip_address

import pytest
from faker import Faker
from waffle.testutils import override_flag

from apps.accounts import models as ac_models
from apps.accounts.factories import (
    ProviderRequestFactory,
    ProviderRequestEvidenceFactory,
    ProviderRequestLocationFactory,
    VerificationBasisFactory,
)
from apps.greencheck.factories import ServiceFactory

faker = Faker()

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Wizard form data fixtures (mirrors test_provider_request.py)
# ---------------------------------------------------------------------------

@pytest.fixture()
def wizard_form_org_details_data():
    return {
        "provider_request_wizard_view-current_step": "0",
        "0-name": " ".join(faker.words(5)),
        "0-website": faker.url(),
        "0-description": faker.sentence(10),
        "0-authorised_by_org": "True",
    }


@pytest.fixture()
def wizard_form_org_location_data():
    return {
        "provider_request_wizard_view-current_step": "1",
        "locations__1-TOTAL_FORMS": "3",
        "locations__1-INITIAL_FORMS": "0",
        "locations__1-0-country": faker.country_code(),
        "locations__1-0-city": faker.city(),
        "locations__1-0-name": "Main HQ",
        "locations__1-1-country": faker.country_code(),
        "locations__1-1-city": faker.city(),
        "locations__1-1-name": "eu-west datacentre",
        "locations__1-2-country": faker.country_code(),
        "locations__1-2-city": faker.city(),
        "locations__1-2-name": "Regional office",
        "extra__1-location_import_required": "True",
    }


@pytest.fixture()
def location_labels_by_name():
    """Indexed labels expected from _get_location_choices for the fixture data.

    Because faker produces variable city/country values, the exact labels cannot
    be hard-coded. Tests that need stable labels should use this map and the
    `location_label_for` helper below.
    """
    return {0: "Main HQ", 1: "eu-west datacentre", 2: "Regional office"}


@pytest.fixture()
def wizard_form_services_data():
    for _ in range(5):
        ServiceFactory.create()
    tags_choices = ac_models.Service.objects.all()
    services_sample = random.sample([tag.slug for tag in tags_choices], 3)
    return {
        "provider_request_wizard_view-current_step": "2",
        "2-services": services_sample,
    }


@pytest.fixture()
def wizard_form_verification_bases_data():
    for _ in range(5):
        VerificationBasisFactory.create()
    choices = ac_models.ProviderRequest.get_verification_bases_choices()
    bases_sample = random.sample([slug for slug, _label in choices], 3)
    return {
        "provider_request_wizard_view-current_step": "3",
        "3-verification_bases": bases_sample,
    }


@pytest.fixture()
def wizard_form_network_data():
    sorted_ips = sorted(
        [faker.ipv4() for _ in range(10)], key=lambda x: ip_address(x)
    )
    return {
        "provider_request_wizard_view-current_step": "5",
        "ips__5-TOTAL_FORMS": "2",
        "ips__5-INITIAL_FORMS": "0",
        "ips__5-0-start": sorted_ips[0],
        "ips__5-0-end": sorted_ips[1],
        "ips__5-1-start": sorted_ips[2],
        "ips__5-1-end": sorted_ips[3],
        "asns__5-TOTAL_FORMS": "1",
        "asns__5-INITIAL_FORMS": "0",
        "asns__5-0-asn": faker.random_int(min=100, max=999),
    }


@pytest.fixture()
def wizard_form_consent():
    return {
        "provider_request_wizard_view-current_step": "6",
        "6-data_processing_opt_in": "on",
        "6-newsletter_opt_in": "off",
    }


@pytest.fixture()
def wizard_form_preview():
    return {
        "provider_request_wizard_view-current_step": "7",
    }


@pytest.fixture()
def wizard_form_evidence_data():
    """
    Standard evidence step payload without region_scope/locations
    (used for the flag-off test).
    """
    return {
        "provider_request_wizard_view-current_step": "4",
        "4-TOTAL_FORMS": 2,
        "4-INITIAL_FORMS": 0,
        "4-0-title": " ".join(faker.words(3)),
        "4-0-link": faker.url(),
        "4-0-file": "",
        "4-0-type": ac_models.EvidenceType.WEB_PAGE.value,
        "4-0-public": "on",
        "4-1-title": " ".join(faker.words(3)),
        "4-1-link": faker.url(),
        "4-1-file": "",
        "4-1-type": ac_models.EvidenceType.ANNUAL_REPORT.value,
        "4-1-public": "on",
    }


@pytest.fixture()
def wizard_form_evidence_data_with_regions_all():
    """
    Evidence step payload that includes region_scope='all' for the first row.
    The wizard_form_org_location_data fixture creates 3 locations.
    """
    return {
        "provider_request_wizard_view-current_step": "4",
        "4-TOTAL_FORMS": 1,
        "4-INITIAL_FORMS": 0,
        "4-0-title": " ".join(faker.words(3)),
        "4-0-link": faker.url(),
        "4-0-file": "",
        "4-0-type": ac_models.EvidenceType.WEB_PAGE.value,
        "4-0-public": "on",
        "4-0-region_scope": "all",
    }


@pytest.fixture()
def wizard_form_evidence_data_with_regions_specific():
    """
    Evidence step payload that includes region_scope='specific' and
    selects location index 1 for the first row.
    """
    return {
        "provider_request_wizard_view-current_step": "4",
        "4-TOTAL_FORMS": 1,
        "4-INITIAL_FORMS": 0,
        "4-0-title": " ".join(faker.words(3)),
        "4-0-link": faker.url(),
        "4-0-file": "",
        "4-0-type": ac_models.EvidenceType.WEB_PAGE.value,
        "4-0-public": "on",
        "4-0-region_scope": "specific",
        "4-0-locations": ["1"],
    }


class TestProviderRequestEvidenceLocation:
    """Tests for the draft through model linking evidence to locations."""

    def test_create_evidence_location_link(self):
        pr = ProviderRequestFactory.create()
        loc = ProviderRequestLocationFactory.create(request=pr)
        evidence = ProviderRequestEvidenceFactory.create(request=pr)

        link = ac_models.ProviderRequestEvidenceLocation.objects.create(
            evidence=evidence, location=loc
        )
        assert link.evidence == evidence
        assert link.location == loc

    def test_unique_together(self):
        pr = ProviderRequestFactory.create()
        loc = ProviderRequestLocationFactory.create(request=pr)
        evidence = ProviderRequestEvidenceFactory.create(request=pr)

        ac_models.ProviderRequestEvidenceLocation.objects.create(
            evidence=evidence, location=loc
        )
        with pytest.raises(Exception):
            ac_models.ProviderRequestEvidenceLocation.objects.create(
                evidence=evidence, location=loc
            )

    def test_cascade_delete_evidence(self):
        pr = ProviderRequestFactory.create()
        loc = ProviderRequestLocationFactory.create(request=pr)
        evidence = ProviderRequestEvidenceFactory.create(request=pr)
        ac_models.ProviderRequestEvidenceLocation.objects.create(
            evidence=evidence, location=loc
        )
        assert ac_models.ProviderRequestEvidenceLocation.objects.count() == 1
        evidence.delete()
        assert ac_models.ProviderRequestEvidenceLocation.objects.count() == 0

    def test_cascade_delete_location(self):
        pr = ProviderRequestFactory.create()
        loc = ProviderRequestLocationFactory.create(request=pr)
        evidence = ProviderRequestEvidenceFactory.create(request=pr)
        ac_models.ProviderRequestEvidenceLocation.objects.create(
            evidence=evidence, location=loc
        )
        assert ac_models.ProviderRequestEvidenceLocation.objects.count() == 1
        loc.delete()
        assert ac_models.ProviderRequestEvidenceLocation.objects.count() == 0

    def test_evidence_locations_m2m(self):
        pr = ProviderRequestFactory.create()
        loc1 = ProviderRequestLocationFactory.create(request=pr)
        loc2 = ProviderRequestLocationFactory.create(request=pr)
        evidence = ProviderRequestEvidenceFactory.create(request=pr)

        ac_models.ProviderRequestEvidenceLocation.objects.create(
            evidence=evidence, location=loc1
        )
        ac_models.ProviderRequestEvidenceLocation.objects.create(
            evidence=evidence, location=loc2
        )

        assert set(evidence.locations.all()) == {loc1, loc2}


class TestHostingProviderSupportingDocumentLocation:
    """Tests for the live through model linking documents to locations."""

    def test_create_document_location_link(self, hosting_provider):
        hosting_provider.save()
        loc = ac_models.HostingProviderLocation.objects.create(
            hostingprovider=hosting_provider,
            city="Amsterdam",
            country="NL",
        )
        doc = ac_models.HostingProviderSupportingDocument.objects.create(
            hostingprovider=hosting_provider,
            title="Test doc",
            type=ac_models.EvidenceType.ANNUAL_REPORT,
            valid_from="2026-01-01",
            valid_to="2026-12-31",
        )
        link = ac_models.HostingProviderSupportingDocumentLocation.objects.create(
            document=doc, location=loc
        )
        assert link.document == doc
        assert link.location == loc

    def test_unique_together(self, hosting_provider):
        hosting_provider.save()
        loc = ac_models.HostingProviderLocation.objects.create(
            hostingprovider=hosting_provider,
            city="Berlin",
            country="DE",
        )
        doc = ac_models.HostingProviderSupportingDocument.objects.create(
            hostingprovider=hosting_provider,
            title="Test doc",
            type=ac_models.EvidenceType.ANNUAL_REPORT,
            valid_from="2026-01-01",
            valid_to="2026-12-31",
        )
        ac_models.HostingProviderSupportingDocumentLocation.objects.create(
            document=doc, location=loc
        )
        with pytest.raises(Exception):
            ac_models.HostingProviderSupportingDocumentLocation.objects.create(
                document=doc, location=loc
            )


class TestHostingProviderLocation:
    """Tests for the live location model."""

    def test_is_primary_syncs_flat_fields(self, hosting_provider):
        hosting_provider.save()
        loc = ac_models.HostingProviderLocation.objects.create(
            hostingprovider=hosting_provider,
            city="Paris",
            country="FR",
            is_primary=True,
        )
        hosting_provider.refresh_from_db()
        assert hosting_provider.country == "FR"
        assert hosting_provider.city == "Paris"

    def test_only_one_primary_per_provider(self, hosting_provider):
        hosting_provider.save()
        loc1 = ac_models.HostingProviderLocation.objects.create(
            hostingprovider=hosting_provider,
            city="Paris",
            country="FR",
            is_primary=True,
        )
        loc2 = ac_models.HostingProviderLocation.objects.create(
            hostingprovider=hosting_provider,
            city="Berlin",
            country="DE",
            is_primary=True,
        )
        loc1.refresh_from_db()
        assert loc1.is_primary is False
        assert loc2.is_primary is True

    def test_non_primary_does_not_sync_flat_fields(self, hosting_provider):
        hosting_provider.country = "US"
        hosting_provider.city = "New York"
        hosting_provider.save()
        ac_models.HostingProviderLocation.objects.create(
            hostingprovider=hosting_provider,
            city="Seattle",
            country="US",
            is_primary=False,
        )
        hosting_provider.refresh_from_db()
        assert hosting_provider.city == "New York"


class TestWizardSubmissionWithRegions:
    """Tests for the wizard evidence step with region_scope and locations."""

    def _full_form_data(
        self,
        org_details,
        org_location,
        services,
        verification_bases,
        evidence,
        network,
        consent,
        preview,
    ):
        return [
            org_details,
            org_location,
            services,
            verification_bases,
            evidence,
            network,
            consent,
            preview,
        ]

    @override_flag("link_disclosures_to_regions", active=True)
    def test_wizard_all_regions_links_to_all_locations(
        self,
        user,
        client,
        wizard_form_org_details_data,
        wizard_form_org_location_data,
        wizard_form_services_data,
        wizard_form_verification_bases_data,
        wizard_form_evidence_data_with_regions_all,
        wizard_form_network_data,
        wizard_form_consent,
        wizard_form_preview,
    ):
        """When region_scope='all', evidence is linked to all locations."""
        from django.urls import reverse as urls_reverse

        form_data = self._full_form_data(
            wizard_form_org_details_data,
            wizard_form_org_location_data,
            wizard_form_services_data,
            wizard_form_verification_bases_data,
            wizard_form_evidence_data_with_regions_all,
            wizard_form_network_data,
            wizard_form_consent,
            wizard_form_preview,
        )
        client.force_login(user)

        for step, data in enumerate(form_data, 1):
            response = client.post(urls_reverse("provider_registration"), data, follow=True)
            if step < len(form_data):
                assert response.status_code == 200
                assert response.context_data["wizard"]["steps"].current == str(step)

        pr = ac_models.ProviderRequest.objects.get(name=wizard_form_org_details_data["0-name"])
        locations = pr.providerrequestlocation_set.all()
        assert locations.count() == 3

        evidence = pr.providerrequestevidence_set.first()
        assert evidence is not None
        # All locations should be linked
        assert evidence.locations.count() == 3

    @override_flag("link_disclosures_to_regions", active=True)
    def test_wizard_specific_regions_links_to_selected(
        self,
        user,
        client,
        wizard_form_org_details_data,
        wizard_form_org_location_data,
        wizard_form_services_data,
        wizard_form_verification_bases_data,
        wizard_form_evidence_data_with_regions_specific,
        wizard_form_network_data,
        wizard_form_consent,
        wizard_form_preview,
    ):
        """When region_scope='specific', only selected locations are linked."""
        from django.urls import reverse as urls_reverse

        form_data = self._full_form_data(
            wizard_form_org_details_data,
            wizard_form_org_location_data,
            wizard_form_services_data,
            wizard_form_verification_bases_data,
            wizard_form_evidence_data_with_regions_specific,
            wizard_form_network_data,
            wizard_form_consent,
            wizard_form_preview,
        )
        client.force_login(user)

        for data in form_data:
            client.post(urls_reverse("provider_registration"), data, follow=True)

        pr = ac_models.ProviderRequest.objects.get(name=wizard_form_org_details_data["0-name"])
        locations = list(pr.providerrequestlocation_set.all().order_by("id"))
        assert len(locations) == 3

        evidence = pr.providerrequestevidence_set.first()
        assert evidence is not None
        # Only location index 1 should be linked
        assert evidence.locations.count() == 1
        assert evidence.locations.first() == locations[1]

    def test_wizard_flag_off_auto_all_regions(
        self,
        user,
        client,
        wizard_form_org_details_data,
        wizard_form_org_location_data,
        wizard_form_services_data,
        wizard_form_verification_bases_data,
        wizard_form_evidence_data,
        wizard_form_network_data,
        wizard_form_consent,
        wizard_form_preview,
    ):
        """When the flag is off, evidence is auto-linked to all locations."""
        from django.urls import reverse as urls_reverse

        form_data = self._full_form_data(
            wizard_form_org_details_data,
            wizard_form_org_location_data,
            wizard_form_services_data,
            wizard_form_verification_bases_data,
            wizard_form_evidence_data,
            wizard_form_network_data,
            wizard_form_consent,
            wizard_form_preview,
        )
        client.force_login(user)

        for data in form_data:
            client.post(urls_reverse("provider_registration"), data, follow=True)

        pr = ac_models.ProviderRequest.objects.get(name=wizard_form_org_details_data["0-name"])
        locations = pr.providerrequestlocation_set.all()
        assert locations.count() == 3

        for evidence in pr.providerrequestevidence_set.all():
            assert evidence.locations.count() == 3


class TestApprovalFlow:
    """Tests for ProviderRequest.approve() with region links."""

    def test_approve_creates_live_locations(
        self, hosting_provider, sample_hoster_user
    ):
        """approve() creates HostingProviderLocation rows from submitted locations."""
        hosting_provider.save()
        pr = ProviderRequestFactory.create(
            provider=hosting_provider,
            created_by=sample_hoster_user,
            status=ac_models.ProviderRequestStatus.PENDING_REVIEW,
        )
        ProviderRequestLocationFactory.create(
            request=pr, city="Amsterdam", country="NL"
        )
        ProviderRequestLocationFactory.create(
            request=pr, city="Berlin", country="DE"
        )

        pr.approve()

        hosting_provider.refresh_from_db()
        locations = list(hosting_provider.locations.all().order_by("id"))
        assert len(locations) == 2
        assert locations[0].is_primary is True
        assert locations[1].is_primary is False
        assert locations[0].city == "Amsterdam"
        assert locations[1].city == "Berlin"
        # Flat fields synced from primary
        assert hosting_provider.country == "NL"
        assert hosting_provider.city == "Amsterdam"

    def test_approve_carries_across_region_links(
        self, hosting_provider, sample_hoster_user
    ):
        """approve() carries across disclosure-region links to live models."""
        hosting_provider.save()
        pr = ProviderRequestFactory.create(
            provider=hosting_provider,
            created_by=sample_hoster_user,
            status=ac_models.ProviderRequestStatus.PENDING_REVIEW,
        )
        loc1 = ProviderRequestLocationFactory.create(
            request=pr, city="Amsterdam", country="NL"
        )
        loc2 = ProviderRequestLocationFactory.create(
            request=pr, city="Berlin", country="DE"
        )
        evidence = ProviderRequestEvidenceFactory.create(
            request=pr,
            link="https://example.com/evidence.pdf",
            file=None,
        )
        # Link evidence to both locations
        ac_models.ProviderRequestEvidenceLocation.objects.create(
            evidence=evidence, location=loc1
        )
        ac_models.ProviderRequestEvidenceLocation.objects.create(
            evidence=evidence, location=loc2
        )

        pr.approve()

        hosting_provider.refresh_from_db()
        live_docs = hosting_provider.supporting_documents.all()
        assert live_docs.count() == 1

        live_doc = live_docs.first()
        live_locs = list(live_doc.locations.all().order_by("id"))
        assert len(live_locs) == 2
        assert live_locs[0].city == "Amsterdam"
        assert live_locs[1].city == "Berlin"

    def test_approve_with_all_regions_evidence(
        self, hosting_provider, sample_hoster_user
    ):
        """Evidence linked to all draft locations gets linked to all live locations."""
        hosting_provider.save()
        pr = ProviderRequestFactory.create(
            provider=hosting_provider,
            created_by=sample_hoster_user,
            status=ac_models.ProviderRequestStatus.PENDING_REVIEW,
        )
        loc1 = ProviderRequestLocationFactory.create(
            request=pr, city="Amsterdam", country="NL"
        )
        loc2 = ProviderRequestLocationFactory.create(
            request=pr, city="Berlin", country="DE"
        )
        loc3 = ProviderRequestLocationFactory.create(
            request=pr, city="Paris", country="FR"
        )
        evidence = ProviderRequestEvidenceFactory.create(
            request=pr,
            link="https://example.com/evidence.pdf",
            file=None,
        )
        # Link to all locations
        for loc in [loc1, loc2, loc3]:
            ac_models.ProviderRequestEvidenceLocation.objects.create(
                evidence=evidence, location=loc
            )

        pr.approve()

        hosting_provider.refresh_from_db()
        live_doc = hosting_provider.supporting_documents.first()
        assert live_doc.locations.count() == 3


class TestAdminInlineLocations:
    """Tests for admin inlines with locations field."""

    def test_provider_request_evidence_inline_limits_locations(
        self, sample_hoster_user
    ):
        """The inline form limits locations to the request's locations."""
        from apps.accounts.forms.admin import (
            HostingProviderSupportingDocumentInlineForm,
            InlineSupportingDocumentForm,
        )
        from apps.accounts.admin.provider_request import (
            ProviderRequestEvidenceInlineForm,
        )

        pr = ProviderRequestFactory.create()
        ProviderRequestLocationFactory.create(
            request=pr, city="Amsterdam", country="NL"
        )
        evidence = ProviderRequestEvidenceFactory.create(request=pr)

        form = ProviderRequestEvidenceInlineForm(instance=evidence)
        assert form.fields["locations"].queryset.count() == 1


class TestCredentialFormClean:
    """Unit tests for CredentialForm validation."""

    def test_clean_defaults_to_all_when_flag_off(self):
        """When the flag is off, region_scope defaults to 'all'."""
        from apps.accounts.forms.provider_request_wizard import CredentialForm

        form = CredentialForm(data={
            "type": ac_models.EvidenceType.WEB_PAGE.value,
            "title": "Test evidence",
            "link": "https://example.com",
            "file": "",
            "public": "on",
        })
        assert form.is_valid()
        assert form.cleaned_data["region_scope"] == "all"
        assert form.cleaned_data["locations"] == []

    @override_flag("link_disclosures_to_regions", active=True)
    def test_clean_specific_requires_locations(self):
        """When region_scope is 'specific', locations are required."""
        from django.test import RequestFactory

        from apps.accounts.forms.provider_request_wizard import CredentialForm

        rf = RequestFactory()
        req = rf.get("/")
        req.user = type("U", (), {"is_admin": False})()  # minimal user stub

        form = CredentialForm(
            data={
                "type": ac_models.EvidenceType.WEB_PAGE.value,
                "title": "Test evidence",
                "link": "https://example.com",
                "file": "",
                "public": "on",
                "region_scope": "specific",
                "locations": [],
            },
            location_choices=[("0", "Amsterdam, NL")],
            request=req,
        )
        assert not form.is_valid()
        assert "locations" in form.errors

    @override_flag("link_disclosures_to_regions", active=True)
    def test_clean_all_clears_locations(self):
        """When region_scope is 'all', locations are cleared."""
        from django.test import RequestFactory

        from apps.accounts.forms.provider_request_wizard import CredentialForm

        rf = RequestFactory()
        req = rf.get("/")
        req.user = type("U", (), {"is_admin": False})()  # minimal user stub

        form = CredentialForm(
            data={
                "type": ac_models.EvidenceType.WEB_PAGE.value,
                "title": "Test evidence",
                "link": "https://example.com",
                "file": "",
                "public": "on",
                "region_scope": "all",
                "locations": ["0"],
            },
            location_choices=[("0", "Amsterdam, NL")],
            request=req,
        )
        assert form.is_valid()
        assert form.cleaned_data["locations"] == []
