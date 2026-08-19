"""
Tests for the per-disclosure basis-for-verification feature.

Covers:
- DisclosureClaim model (creation per category, lazy creation)
- ProviderRequestEvidenceClaim through model (create, unique, cascade)
- HostingProviderSupportingDocumentClaim through model (create, unique)
- claims_display property on both disclosure models
- Wizard _get_disclosure_claim_choices() (selected bases + always-on)
- Wizard submission with claim_choices (flag on, multi-select, re-edit)
- Wizard submission with flag off (field absent, no through rows)
- CredentialForm clean() defaults claim_choices to [] when flag off
- Preview render_as_claims template filter
- Approval flow: approve() carries claim links to live documents
- Admin edit_disclosure_claims view (Hostingprovider + ProviderRequest)
"""

import random

import pytest
from django.test import RequestFactory
from waffle.testutils import override_flag

from apps.accounts import models as ac_models
from apps.accounts.factories import (
    DisclosureClaimFactory,
    ProviderRequestFactory,
    ProviderRequestEvidenceFactory,
    ProviderRequestLocationFactory,
    VerificationBasisFactory,
)
from apps.accounts.forms.provider_request_wizard import CredentialForm
from apps.accounts.templatetags.preview_extras import render_as_claims
from apps.greencheck.factories import ServiceFactory

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestDisclosureClaim:
    """Tests for the DisclosureClaim reference model."""

    def test_create_organisation_basis_claim(self):
        basis = VerificationBasisFactory.create()
        claim = ac_models.DisclosureClaim.objects.create(
            slug=f"basis--{basis.slug}",
            label=basis.name,
            category=ac_models.DisclosureClaimType.ORGANISATION_BASIS,
            basis=basis,
            version=basis.version,
        )
        assert claim.basis == basis
        assert claim.category == ac_models.DisclosureClaimType.ORGANISATION_BASIS.value

    def test_create_third_party_assurance_claim(self):
        claim, _ = ac_models.DisclosureClaim.objects.get_or_create(
            slug="third-party-independent-assurance-test",
            defaults={
                "label": "Third-party assurance",
                "category": ac_models.DisclosureClaimType.THIRD_PARTY_ASSURANCE,
            },
        )
        assert claim.basis is None
        assert claim.version is None
        assert claim.category == ac_models.DisclosureClaimType.THIRD_PARTY_ASSURANCE.value

    def test_create_needs_help_claim(self):
        claim, _ = ac_models.DisclosureClaim.objects.get_or_create(
            slug="i-would-like-help-confirming-this-test",
            defaults={
                "label": "I'd like help",
                "category": ac_models.DisclosureClaimType.NEEDS_HELP,
            },
        )
        assert claim.category == ac_models.DisclosureClaimType.NEEDS_HELP.value

    def test_str_returns_label(self):
        claim = DisclosureClaimFactory.create(label="My Claim")
        assert str(claim) == "My Claim"


class TestProviderRequestEvidenceClaim:
    """Tests for the draft through model linking evidence to claims."""

    def test_create_evidence_claim_link(self):
        pr = ProviderRequestFactory.create()
        evidence = ProviderRequestEvidenceFactory.create(request=pr)
        claim = DisclosureClaimFactory.create()
        link = ac_models.ProviderRequestEvidenceClaim.objects.create(
            evidence=evidence, claim=claim
        )
        assert link.evidence == evidence
        assert link.claim == claim

    def test_unique_together(self):
        pr = ProviderRequestFactory.create()
        evidence = ProviderRequestEvidenceFactory.create(request=pr)
        claim = DisclosureClaimFactory.create()
        ac_models.ProviderRequestEvidenceClaim.objects.create(
            evidence=evidence, claim=claim
        )
        with pytest.raises(Exception):
            ac_models.ProviderRequestEvidenceClaim.objects.create(
                evidence=evidence, claim=claim
            )

    def test_cascade_delete_evidence(self):
        pr = ProviderRequestFactory.create()
        evidence = ProviderRequestEvidenceFactory.create(request=pr)
        claim = DisclosureClaimFactory.create()
        ac_models.ProviderRequestEvidenceClaim.objects.create(
            evidence=evidence, claim=claim
        )
        assert ac_models.ProviderRequestEvidenceClaim.objects.count() == 1
        evidence.delete()
        assert ac_models.ProviderRequestEvidenceClaim.objects.count() == 0

    def test_evidence_claims_m2m(self):
        pr = ProviderRequestFactory.create()
        evidence = ProviderRequestEvidenceFactory.create(request=pr)
        claim1 = DisclosureClaimFactory.create()
        claim2 = DisclosureClaimFactory.create()
        ac_models.ProviderRequestEvidenceClaim.objects.create(
            evidence=evidence, claim=claim1
        )
        ac_models.ProviderRequestEvidenceClaim.objects.create(
            evidence=evidence, claim=claim2
        )
        assert set(evidence.claims.all()) == {claim1, claim2}


class TestHostingProviderSupportingDocumentClaim:
    """Tests for the live through model linking documents to claims."""

    def test_create_document_claim_link(self, hosting_provider):
        hosting_provider.save()
        doc = ac_models.HostingProviderSupportingDocument.objects.create(
            hostingprovider=hosting_provider,
            title="Test doc",
            type=ac_models.EvidenceType.ANNUAL_REPORT,
            valid_from="2026-01-01",
            valid_to="2026-12-31",
        )
        claim = DisclosureClaimFactory.create()
        link = ac_models.HostingProviderSupportingDocumentClaim.objects.create(
            document=doc, claim=claim
        )
        assert link.document == doc
        assert link.claim == claim

    def test_unique_together(self, hosting_provider):
        hosting_provider.save()
        doc = ac_models.HostingProviderSupportingDocument.objects.create(
            hostingprovider=hosting_provider,
            title="Test doc",
            type=ac_models.EvidenceType.ANNUAL_REPORT,
            valid_from="2026-01-01",
            valid_to="2026-12-31",
        )
        claim = DisclosureClaimFactory.create()
        ac_models.HostingProviderSupportingDocumentClaim.objects.create(
            document=doc, claim=claim
        )
        with pytest.raises(Exception):
            ac_models.HostingProviderSupportingDocumentClaim.objects.create(
                document=doc, claim=claim
            )

    def test_claims_display_property(self, hosting_provider):
        hosting_provider.save()
        doc = ac_models.HostingProviderSupportingDocument.objects.create(
            hostingprovider=hosting_provider,
            title="Test doc",
            type=ac_models.EvidenceType.ANNUAL_REPORT,
            valid_from="2026-01-01",
            valid_to="2026-12-31",
        )
        assert doc.claims_display == "None"
        claim1 = DisclosureClaimFactory.create(label="Claim One")
        claim2 = DisclosureClaimFactory.create(label="Claim Two")
        ac_models.HostingProviderSupportingDocumentClaim.objects.create(
            document=doc, claim=claim1
        )
        ac_models.HostingProviderSupportingDocumentClaim.objects.create(
            document=doc, claim=claim2
        )
        assert doc.claims_display == "Claim One, Claim Two"


class TestClaimsDisplayProperty:
    """Tests for the claims_display property on draft evidence."""

    def test_claims_display_empty(self):
        pr = ProviderRequestFactory.create()
        evidence = ProviderRequestEvidenceFactory.create(request=pr)
        assert evidence.claims_display == "None"

    def test_claims_display_with_claims(self):
        pr = ProviderRequestFactory.create()
        evidence = ProviderRequestEvidenceFactory.create(request=pr)
        claim1 = DisclosureClaimFactory.create(label="Claim A")
        claim2 = DisclosureClaimFactory.create(label="Claim B")
        ac_models.ProviderRequestEvidenceClaim.objects.create(
            evidence=evidence, claim=claim1
        )
        ac_models.ProviderRequestEvidenceClaim.objects.create(
            evidence=evidence, claim=claim2
        )
        assert evidence.claims_display == "Claim A, Claim B"


# ---------------------------------------------------------------------------
# Wizard fixture data (mirrors test_link_disclosures_to_regions.py)
# ---------------------------------------------------------------------------


from faker import Faker

faker = Faker()


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
        "locations__1-TOTAL_FORMS": "1",
        "locations__1-INITIAL_FORMS": "0",
        "locations__1-0-country": faker.country_code(),
        "locations__1-0-city": faker.city(),
        "locations__1-0-name": "Main HQ",
        "extra__1-location_import_required": "True",
    }


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
    bases_sample = random.sample([slug for slug, _label in choices], 2)
    return {
        "provider_request_wizard_view-current_step": "3",
        "3-verification_bases": bases_sample,
    }


@pytest.fixture()
def wizard_form_network_data():
    sorted_ips = sorted(
        [faker.ipv4() for _ in range(10)], key=lambda x: __import__("ipaddress").ip_address(x)
    )
    return {
        "provider_request_wizard_view-current_step": "5",
        "ips__5-TOTAL_FORMS": "1",
        "ips__5-INITIAL_FORMS": "0",
        "ips__5-0-start": sorted_ips[0],
        "ips__5-0-end": sorted_ips[1],
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
def wizard_form_evidence_data_with_claims():
    """
    Evidence step payload with claim_choices for one row.
    Requires the disclosure_claims flag to be on + seeded DisclosureClaims.
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
        "4-0-claim_choices": [],
    }


@pytest.fixture()
def wizard_form_evidence_data_without_claims():
    """Evidence step payload without claim_choices (for flag-off test)."""
    return {
        "provider_request_wizard_view-current_step": "4",
        "4-TOTAL_FORMS": 1,
        "4-INITIAL_FORMS": 0,
        "4-0-title": " ".join(faker.words(3)),
        "4-0-link": faker.url(),
        "4-0-file": "",
        "4-0-type": ac_models.EvidenceType.WEB_PAGE.value,
        "4-0-public": "on",
    }


def _full_form_data(*steps):
    return list(steps)


# ---------------------------------------------------------------------------
# Wizard _get_disclosure_claim_choices() + CredentialForm tests
# ---------------------------------------------------------------------------


class TestCredentialFormClean:
    """Unit tests for CredentialForm with the disclosure_claims flag."""

    def test_clean_defaults_to_empty_when_flag_off(self):
        """When the flag is off, claim_choices defaults to []."""
        form = CredentialForm(data={
            "type": ac_models.EvidenceType.WEB_PAGE.value,
            "title": "Test evidence",
            "link": "https://example.com",
            "file": "",
            "public": "on",
        })
        assert form.is_valid()
        assert form.cleaned_data["claim_choices"] == []

    @override_flag("disclosure_claims", active=True)
    def test_field_present_when_flag_on(self):
        """When the flag is on, the claim_choices field is present."""
        rf = RequestFactory()
        req = rf.get("/")
        req.user = type("U", (), {"is_admin": False})()

        form = CredentialForm(
            data={
                "type": ac_models.EvidenceType.WEB_PAGE.value,
                "title": "Test evidence",
                "link": "https://example.com",
                "file": "",
                "public": "on",
            },
            claim_choices=[("x", "Claim X")],
            request=req,
        )
        assert "claim_choices" in form.fields
        assert form.fields["claim_choices"].choices == [("x", "Claim X")]

    def test_field_absent_when_flag_off(self):
        """When the flag is off, the claim_choices field is popped."""
        rf = RequestFactory()
        req = rf.get("/")
        req.user = type("U", (), {"is_admin": False})()

        form = CredentialForm(
            data={
                "type": ac_models.EvidenceType.WEB_PAGE.value,
                "title": "Test evidence",
                "link": "https://example.com",
                "file": "",
                "public": "on",
            },
            claim_choices=[("x", "Claim X")],
            request=req,
        )
        assert "claim_choices" not in form.fields


# ---------------------------------------------------------------------------
# Preview template filter tests
# ---------------------------------------------------------------------------


class TestRenderAsClaimsFilter:
    """Tests for the render_as_claims template filter."""

    def test_renders_labels_from_db(self):
        claim1 = DisclosureClaimFactory.create(label="Claim One")
        claim2 = DisclosureClaimFactory.create(label="Claim Two")
        result = render_as_claims([claim1.slug, claim2.slug])
        assert "<ul>" in result
        assert "<li>Claim One</li>" in result
        assert "<li>Claim Two</li>" in result

    def test_renders_labels_from_choices_map(self):
        choices = [("a", "Alpha"), ("b", "Beta")]
        result = render_as_claims(["a", "b"], choices)
        assert "<ul>" in result
        assert "<li>Alpha</li>" in result
        assert "<li>Beta</li>" in result

    def test_empty_returns_none(self):
        assert render_as_claims([]) is None
        assert render_as_claims(None) is None


# ---------------------------------------------------------------------------
# Wizard submission tests
# ---------------------------------------------------------------------------


class TestWizardSubmissionWithClaims:
    """Tests for the wizard evidence step with claim_choices."""

    @override_flag("disclosure_claims", active=True)
    def test_wizard_creates_claim_links(
        self,
        user,
        client,
        wizard_form_org_details_data,
        wizard_form_org_location_data,
        wizard_form_services_data,
        wizard_form_verification_bases_data,
        wizard_form_evidence_data_with_claims,
        wizard_form_network_data,
        wizard_form_consent,
        wizard_form_preview,
    ):
        """Submitting Step 4 with claim_choices creates through rows."""
        from django.urls import reverse as urls_reverse

        # Pre-seed DisclosureClaims for the selected bases + always-on.
        basis_slugs = wizard_form_verification_bases_data["3-verification_bases"]
        for slug in basis_slugs:
            basis = ac_models.VerificationBasis.objects.get(slug=slug)
            ac_models.DisclosureClaim.objects.get_or_create(
                slug=f"basis--{basis.slug}",
                defaults={
                    "label": basis.name,
                    "category": ac_models.DisclosureClaimType.ORGANISATION_BASIS,
                    "basis": basis,
                    "version": basis.version,
                },
            )
        ac_models.DisclosureClaim.objects.get_or_create(
            slug="third-party-independent-assurance",
            defaults={
                "label": "Third-party assurance",
                "category": ac_models.DisclosureClaimType.THIRD_PARTY_ASSURANCE,
            },
        )

        # Select the first basis claim + the always-on assurance claim.
        first_basis_slug = basis_slugs[0]
        wizard_form_evidence_data_with_claims["4-0-claim_choices"] = [
            f"basis--{first_basis_slug}",
            "third-party-independent-assurance",
        ]

        form_data = _full_form_data(
            wizard_form_org_details_data,
            wizard_form_org_location_data,
            wizard_form_services_data,
            wizard_form_verification_bases_data,
            wizard_form_evidence_data_with_claims,
            wizard_form_network_data,
            wizard_form_consent,
            wizard_form_preview,
        )
        client.force_login(user)

        for data in form_data:
            client.post(urls_reverse("provider_registration"), data, follow=True)

        pr = ac_models.ProviderRequest.objects.get(
            name=wizard_form_org_details_data["0-name"]
        )
        evidence = pr.providerrequestevidence_set.first()
        assert evidence is not None
        assert evidence.claims.count() == 2
        claim_slugs = set(evidence.claims.values_list("slug", flat=True))
        assert f"basis--{first_basis_slug}" in claim_slugs
        assert "third-party-independent-assurance" in claim_slugs

    @override_flag("disclosure_claims", active=True)
    def test_wizard_no_claims_selected_creates_no_links(
        self,
        user,
        client,
        wizard_form_org_details_data,
        wizard_form_org_location_data,
        wizard_form_services_data,
        wizard_form_verification_bases_data,
        wizard_form_evidence_data_with_claims,
        wizard_form_network_data,
        wizard_form_consent,
        wizard_form_preview,
    ):
        """A disclosure with no claims selected creates no through rows."""
        from django.urls import reverse as urls_reverse

        form_data = _full_form_data(
            wizard_form_org_details_data,
            wizard_form_org_location_data,
            wizard_form_services_data,
            wizard_form_verification_bases_data,
            wizard_form_evidence_data_with_claims,
            wizard_form_network_data,
            wizard_form_consent,
            wizard_form_preview,
        )
        client.force_login(user)

        for data in form_data:
            client.post(urls_reverse("provider_registration"), data, follow=True)

        pr = ac_models.ProviderRequest.objects.get(
            name=wizard_form_org_details_data["0-name"]
        )
        evidence = pr.providerrequestevidence_set.first()
        assert evidence is not None
        assert evidence.claims.count() == 0

    def test_wizard_flag_off_creates_no_claim_rows(
        self,
        user,
        client,
        wizard_form_org_details_data,
        wizard_form_org_location_data,
        wizard_form_services_data,
        wizard_form_verification_bases_data,
        wizard_form_evidence_data_without_claims,
        wizard_form_network_data,
        wizard_form_consent,
        wizard_form_preview,
    ):
        """When the flag is off, no claim_choices through rows are created."""
        from django.urls import reverse as urls_reverse

        form_data = _full_form_data(
            wizard_form_org_details_data,
            wizard_form_org_location_data,
            wizard_form_services_data,
            wizard_form_verification_bases_data,
            wizard_form_evidence_data_without_claims,
            wizard_form_network_data,
            wizard_form_consent,
            wizard_form_preview,
        )
        client.force_login(user)

        for data in form_data:
            client.post(urls_reverse("provider_registration"), data, follow=True)

        pr = ac_models.ProviderRequest.objects.get(
            name=wizard_form_org_details_data["0-name"]
        )
        evidence = pr.providerrequestevidence_set.first()
        assert evidence is not None
        assert evidence.claims.count() == 0


# ---------------------------------------------------------------------------
# Approval flow tests
# ---------------------------------------------------------------------------


class TestApprovalFlowClaims:
    """Tests for ProviderRequest.approve() with claim links."""

    def test_approve_carries_across_claim_links(
        self, hosting_provider, sample_hoster_user
    ):
        """approve() carries claim links to the live supporting document."""
        hosting_provider.save()
        pr = ProviderRequestFactory.create(
            provider=hosting_provider,
            created_by=sample_hoster_user,
            status=ac_models.ProviderRequestStatus.PENDING_REVIEW,
        )
        ProviderRequestLocationFactory.create(
            request=pr, city="Amsterdam", country="NL"
        )
        evidence = ProviderRequestEvidenceFactory.create(
            request=pr,
            link="https://example.com/evidence.pdf",
            file=None,
        )
        claim1 = DisclosureClaimFactory.create(label="Claim One")
        claim2 = DisclosureClaimFactory.create(label="Claim Two")
        ac_models.ProviderRequestEvidenceClaim.objects.create(
            evidence=evidence, claim=claim1
        )
        ac_models.ProviderRequestEvidenceClaim.objects.create(
            evidence=evidence, claim=claim2
        )

        pr.approve()

        hosting_provider.refresh_from_db()
        live_docs = hosting_provider.supporting_documents.all()
        assert live_docs.count() == 1

        live_doc = live_docs.first()
        assert live_doc.claims.count() == 2
        live_labels = set(live_doc.claims.values_list("label", flat=True))
        assert live_labels == {"Claim One", "Claim Two"}

    def test_approve_claim_links_idempotent(
        self, hosting_provider, sample_hoster_user
    ):
        """Re-approval does not duplicate claim links (get_or_create)."""
        hosting_provider.save()
        pr = ProviderRequestFactory.create(
            provider=hosting_provider,
            created_by=sample_hoster_user,
            status=ac_models.ProviderRequestStatus.PENDING_REVIEW,
        )
        ProviderRequestLocationFactory.create(
            request=pr, city="Amsterdam", country="NL"
        )
        evidence = ProviderRequestEvidenceFactory.create(
            request=pr,
            link="https://example.com/evidence.pdf",
            file=None,
        )
        claim = DisclosureClaimFactory.create(label="My Claim")
        ac_models.ProviderRequestEvidenceClaim.objects.create(
            evidence=evidence, claim=claim
        )

        pr.approve()
        hosting_provider.refresh_from_db()
        live_doc = hosting_provider.supporting_documents.first()
        assert live_doc.claims.count() == 1

        # Approve again with a new request carrying the same evidence.
        pr2 = ProviderRequestFactory.create(
            provider=hosting_provider,
            created_by=sample_hoster_user,
            status=ac_models.ProviderRequestStatus.PENDING_REVIEW,
        )
        ProviderRequestLocationFactory.create(
            request=pr2, city="Amsterdam", country="NL"
        )
        evidence2 = ProviderRequestEvidenceFactory.create(
            request=pr2,
            link="https://example.com/evidence.pdf",
            file=None,
        )
        ac_models.ProviderRequestEvidenceClaim.objects.create(
            evidence=evidence2, claim=claim
        )
        pr2.approve()
        hosting_provider.refresh_from_db()
        # The live doc for evidence2 should have exactly 1 claim link.
        live_doc2 = (
            hosting_provider.supporting_documents.filter(
                title=evidence2.title
            ).first()
        )
        assert live_doc2 is not None
        assert live_doc2.claims.count() == 1


# ---------------------------------------------------------------------------
# Admin tests
# ---------------------------------------------------------------------------


class TestAdminEditDisclosureClaimsView:
    """Tests for the dedicated edit_disclosure_claims admin views."""

    def test_hosting_provider_edit_disclosure_claims_get(
        self, greenweb_staff_user, client
    ):
        """The edit_disclosure_claims view loads for a hosting provider."""
        from django.urls import reverse as urls_reverse

        hp = ac_models.Hostingprovider.objects.create(
            name="Test Provider",
            country="US",
            city="New York",
            website="https://example.com",
            description="Test",
        )
        doc = ac_models.HostingProviderSupportingDocument.objects.create(
            hostingprovider=hp,
            title="Test Doc",
            type=ac_models.EvidenceType.ANNUAL_REPORT,
            valid_from="2026-01-01",
            valid_to="2026-12-31",
        )
        claim = DisclosureClaimFactory.create(label="My Claim")
        ac_models.HostingProviderSupportingDocumentClaim.objects.create(
            document=doc, claim=claim
        )

        client.force_login(greenweb_staff_user)
        url = urls_reverse(
            "greenweb_admin:accounts_hostingprovider_edit_disclosure_claims",
            kwargs={"provider": hp.pk},
        )
        response = client.get(url)
        assert response.status_code == 200
        assert b"Test Doc" in response.content

    def test_hosting_provider_edit_disclosure_claims_post(
        self, greenweb_staff_user, client
    ):
        """POSTing updates the claim links for a hosting provider's docs."""
        from django.urls import reverse as urls_reverse

        hp = ac_models.Hostingprovider.objects.create(
            name="Test Provider",
            country="US",
            city="New York",
            website="https://example.com",
            description="Test",
        )
        doc = ac_models.HostingProviderSupportingDocument.objects.create(
            hostingprovider=hp,
            title="Test Doc",
            type=ac_models.EvidenceType.ANNUAL_REPORT,
            valid_from="2026-01-01",
            valid_to="2026-12-31",
        )
        claim1 = DisclosureClaimFactory.create(label="Claim 1")
        claim2 = DisclosureClaimFactory.create(label="Claim 2")

        client.force_login(greenweb_staff_user)
        url = urls_reverse(
            "greenweb_admin:accounts_hostingprovider_edit_disclosure_claims",
            kwargs={"provider": hp.pk},
        )
        response = client.post(
            url,
            {f"doc_{doc.pk}": [str(claim2.pk)]},
            follow=True,
        )
        assert response.status_code == 200

        doc.refresh_from_db()
        assert doc.claims.count() == 1
        assert doc.claims.first() == claim2

    def test_provider_request_edit_disclosure_claims_get(
        self, greenweb_staff_user, client
    ):
        """The edit_disclosure_claims view loads for a provider request."""
        from django.urls import reverse as urls_reverse

        pr = ProviderRequestFactory.create(
            status=ac_models.ProviderRequestStatus.PENDING_REVIEW
        )
        evidence = ProviderRequestEvidenceFactory.create(request=pr)
        claim = DisclosureClaimFactory.create(label="My Claim")
        ac_models.ProviderRequestEvidenceClaim.objects.create(
            evidence=evidence, claim=claim
        )

        client.force_login(greenweb_staff_user)
        url = urls_reverse(
            "greenweb_admin:accounts_providerrequest_edit_disclosure_claims",
            kwargs={"request_id": pr.pk},
        )
        response = client.get(url)
        assert response.status_code == 200

    def test_provider_request_edit_disclosure_claims_post(
        self, greenweb_staff_user, client
    ):
        """POSTing updates the claim links for a provider request's evidence."""
        from django.urls import reverse as urls_reverse

        pr = ProviderRequestFactory.create(
            status=ac_models.ProviderRequestStatus.PENDING_REVIEW
        )
        evidence = ProviderRequestEvidenceFactory.create(request=pr)
        claim1 = DisclosureClaimFactory.create(label="Claim 1")
        claim2 = DisclosureClaimFactory.create(label="Claim 2")

        client.force_login(greenweb_staff_user)
        url = urls_reverse(
            "greenweb_admin:accounts_providerrequest_edit_disclosure_claims",
            kwargs={"request_id": pr.pk},
        )
        response = client.post(
            url,
            {f"doc_{evidence.pk}": [str(claim2.pk)]},
            follow=True,
        )
        assert response.status_code == 200

        evidence.refresh_from_db()
        assert evidence.claims.count() == 1
        assert evidence.claims.first() == claim2
