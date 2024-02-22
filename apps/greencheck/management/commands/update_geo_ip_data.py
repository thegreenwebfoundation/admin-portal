from django.core.management.base import BaseCommand
import tarfile
import shutil
import requests
from django.conf import settings


class Command(BaseCommand):
    help = "Import Geo IP data from Geo IP Provider"

    def _fetch_latest_tarfile(self):
        """
        Fetch the latest Geo IP data tarball from Maxmind,
        using the credentials to authenticate.
        """
        fetch_url = settings.GEOIP_PROVIDER_DOWNLOAD_URL
        username = settings.GEOIP_USER
        password = settings.GEOIP_PASSWORD
        output_file = "maxmind.geolite2-city.tar.gz"

        if not username or not password:
            raise ValueError("GEOIP_USER and GEOIP_PASSWORD must be set")

        response = requests.get(
            fetch_url,
            auth=(username, password),
        )
        with open(output_file, "wb") as f:
            f.write(response.content)

    def _extract_ip_db_from_tarfile(self):
        # Path to the tarball and the file to be extracted
        tarball_path = "maxmind.geolite2-city.tar.gz"
        file_to_extract = "GeoLite2-City.mmdb"

        # Open the tarball
        with tarfile.open(tarball_path, "r:gz") as tar:
            # Extract the file
            # We don't know the name of the enclosing directory,
            # so we have filter for a file path that matches
            # GeoLite2-City.mmdb
            mmdb_file, *rest = [
                filename for filename in tar.getnames() if file_to_extract in filename
            ]
            mmdb_file = tar.extractfile(mmdb_file)
            with open("GeoLite2-City.mmdb", "wb") as f:
                f.write(mmdb_file.read())

    def _move_ip_db_to_destination(self):
        # Destination path for the extracted file
        destination_path = settings.GEOIP_PATH
        # Check if the file already exists in the destination and
        # overwrite if necessary
        if destination_path.exists():
            settings.GEOIP_PATH.unlink()
        shutil.move("GeoLite2-City.mmdb", destination_path)

    def handle(self, *args, **options):

        self._fetch_latest_tarfile()
        self._extract_ip_db_from_tarfile()
        self._move_ip_db_to_destination()

        self.stdout.write(self.style.SUCCESS("Geo IP data imported successfully"))
