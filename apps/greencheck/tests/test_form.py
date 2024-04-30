import logging
import pathlib
import pytest
from django.conf import settings
from django.core.files.base import File
from faker import Faker

from ..forms import ImporterCSVForm

logger = logging.getLogger(__name__)
faker = Faker()


@pytest.fixture
def importer_form_csv_file() -> File:
    csv_path = (
        pathlib.Path(settings.ROOT)
        / "apps"
        / "greencheck"
        / "fixtures"
        / "test_dataset.csv"
    )
    csv_file = File(open(csv_path, "rb"), name="sample_dataset.csv")

    return csv_file


class TestImporterCSVForm:
    def test_form_valid(self, db, hosting_provider, importer_form_csv_file):

        hosting_provider.save()
        form_data = {"provider": hosting_provider.id, "skip_preview": False}

        form = ImporterCSVForm(
            data=form_data, files={"csv_file": importer_form_csv_file}
        )

        assert form.is_valid()

    def test_form_importer_previews(self, db, hosting_provider, importer_form_csv_file):
        hosting_provider.save()
        form_data = {"provider": hosting_provider.id, "skip_preview": False}

        form = ImporterCSVForm(
            data=form_data, files={"csv_file": importer_form_csv_file}
        )

        assert form.is_valid()
        form.save()

        assert len(form.ip_ranges) == 5
        hosting_provider.refresh_from_db()
        assert hosting_provider.greencheckip_set.all().count() == 4
        assert hosting_provider.greencheckasn_set.all().count() == 1

    def test_form_importer_imports_when_preview_disabled(
        self, db, hosting_provider, importer_form_csv_file
    ):
        """
        Running the importer without the preview adds the ip ranges, AS numbers
        and so on to the provider
        """
        hosting_provider.save()
        form_data = {"provider": hosting_provider.id, "skip_preview": True}

        form = ImporterCSVForm(
            data=form_data, files={"csv_file": importer_form_csv_file}
        )

        assert form.is_valid()

        # saving triggers the importer.process
        form.save()

        assert len(form.ip_ranges) == 5
        hosting_provider.refresh_from_db()
        # breakpoint()
        assert hosting_provider.greencheckip_set.all().count() > 0
        assert hosting_provider.greencheckasn_set.all().count() > 0
