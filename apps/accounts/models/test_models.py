import pytest

from apps.accounts.models import Datacenter
from apps.accounts.models.choices import ModelType

# TODO these hit the database, when they probably don't need to, and this will make tests slow. If we can test that these objects are valid another way we should - maybe checking at the field level, or form level.

class TestDatacenter:

    @pytest.mark.parametrize("accounting_model", ("groeneenergie","mixed","compensatie",))
    def test_accepted_ways_to_model(self, hosting_provider, db, accounting_model):
        val, *_ = [
            choice for choice in
            ModelType.choices
            if choice[0] == accounting_model
        ]

        # if we don't have an allowed value this should throw an error
        hosting_provider.model = accounting_model
        hosting_provider.save()

        assert hosting_provider.model == accounting_model

class TestHostingProvider:

    @pytest.mark.parametrize("accounting_model", ("groeneenergie","mixed","compensatie",))
    def test_accepted_ways_to_model(self, datacenter, db, sample_hoster_user, accounting_model, hosting_provider):

        hosting_provider.save()
        sample_hoster_user.hostingprovider = hosting_provider
        sample_hoster_user.save()


        val, *_ = [
            choice for choice in
            ModelType.choices
            if choice[0] == accounting_model
        ]

        # if we don't have an allowed value this should throw an error
        datacenter.model = accounting_model
        datacenter.user_id = sample_hoster_user.id
        datacenter.save()

        assert datacenter.model == accounting_model