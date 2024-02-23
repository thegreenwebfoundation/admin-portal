### Automated Importers

As mentioned in [recurring tasks](/recurring-tasks.md), the green web platform has a set of automated importers designed for bulk import of IP ranges from very large providers. This section details their design, and how to create new ones.

### Two moving parts - NetworkImporter and a CloudImporter

#### TheNetworkImporter

At a high level , importing IP ranges relies on two different moving parts - a `NetworkImporter` and `CloudImporter`.

A NetworkImporter is responsible for:

- taking a list of Ip Ranges or AS nunbers, and associating them with the a given hosting provider
- making sure the correct set of IP ranges or AS numbers are active

#### CloudImporters

At present, the large provider importers include a GoogleImporter, MicrosoftImporter, and a AmazonImporter, which for convenience, we refer to as CloudImporters.

Each of these classes are responsible for:

- fetching the most recent information about a provider from a known location online
- reformatting the fetched data into a form that the an instance of a NetworkImporter can easily consume, to update the IP Ranges and ASN numbers associated with a given provider.

These cloud importers, rather than inheriting from a subclass all confirm to a specific protocol, defined in `ImporterProtocol`. Each of the specific cloud importers implements the following 

```python

class ImporterProtocol(Protocol):
    def fetch_data_from_source(self) -> str:
        """
        Fetches the data, and returns text for parsing, then
        shaping with `parse_to_list`
        """
        raise NotImplementedError

    def parse_to_list(self, raw_data) -> List[Union[str, Tuple]]:
        """
        Returns a list of either strings that can be
        parsed as AS numbers or IP networks, or tuples
        representing IP ranges
        """
        raise NotImplementedError

    def process(self, str) -> dict:
        """
        Return a list of all the create networks as a result of
        running the importer, keyed by the kind of network, and whether
        it was created.
        """
        raise NotImplementedError
```

While `fetch_data_from_source`, `parse_to_list` may give clues to their purpose, `process` is does the actual work of sending the reshaped data to the `NetworkImporter`, and most implememtations work like the example below.


```python
def process(self, list_of_addresses):
    provider_id = settings.provider_id
    provider = Hostingprovider.objects.get(id=provider_id)

    network_importer = NetworkImporter(provider)
    network_importer.deactivate_ips()
    return network_importer.process_addresses(list_of_addresses)

```

In this exmaple, the process method on an CloudImporter object will:

1. Determine the provider to update
2. Deactivate any existing networks associated with the provider (to account for IP addresses being returned to registrars like RIPE)
3. Add, or reactivate the provider networks based on the provided IP and AS data


Checking that importers work as expected:


We check that a cloud importer conforms to this protocol with an assertion in the same file used to define a cloud importer. For example, in the file we define the MicrosoftImporter, we assert that it follows this protocol with the following line.

```
assert isinstance(MicrosoftImporter(), ImporterProtocol)
```

CloudImporters should also have tests, that demonstrate reshaping of fetched data. 


### Running the import from the command line

The most commmon way to run an import from a large provider is on a recurring cronjob, from a django management command.

An simplified managemenrt command looks like the example below - when someone types 

```
python ./manage.py update_networks_in_db_google
```

The `handle` method is called, carrying out the steps we see below, excercising the three methods defined above.

```python

class Command(BaseCommand):
    help = "Update IP ranges for cloud providers that publish them"

    def handle(self, *args, **options):
        importer = GoogleImporter()
        data = importer.fetch_data_from_source()
        parsed_data = importer.parse_to_list(data)
        result = importer.process(parsed_data)

        update_message = (
            f"Processing complete. "
            "(Details about abridged for readability)"
        )
        self.stdout.write(update_message)
```

### Adding new importers

The existing importers were created because three large providers effectivelt make up more than two thirds of the cloud market - us creating this was a fast way to ensure good coverage.

To create new importers, take the following steps:

1. Create a new importer class, satisfying the `ImporterProtocol`
2. Create a management command to allow the importer to be run on a schedule.
3. Add the management command to to the script defined in `import_ips_for_large_providers.sh.j2`, checking if any extra environment variables need to be added, to make sure the importer is updating the correct provider.
