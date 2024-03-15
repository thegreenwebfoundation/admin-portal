# Automated Importers

As mentioned in [recurring tasks](recurring-tasks.md), the green web platform has a set of automated importers designed for bulk import of IP ranges from very large providers. This section details their design, and how to create new ones.

### Two moving parts - NetworkImporter and a CloudImporter

At a high level, importing IP ranges relies on two different moving parts - a `NetworkImporter` and `CloudImporter`.

#### NetworkImporter

A NetworkImporter is responsible for:

- taking a list of IP Ranges or AS nunbers, and associating them with the a given hosting provider
- making sure the correct set of IP ranges or AS numbers are active

#### CloudImporters

At present, the large provider importers include a `GoogleImporter`, `MicrosoftImporter`, and a `AmazonImporter`. For convenience, we refer to as CloudImporters.

Each of these classes are responsible for:

- fetching the most recent network information about a provider from a known location online (i.e https://ip-ranges.amazonaws.com/ip-ranges.json, and so on)
- reformatting this fetched data into a form that an instance of a `NetworkImporter` can easily consume, to update the IP Ranges and ASN numbers associated with a given provider.

These cloud importers, rather than inheriting from a subclass all confirm to a specific protocol, defined in the class `ImporterProtocol`. Each of the specific cloud importers implements the following methods: 

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

While `fetch_data_from_source`, `parse_to_list` may give clues to their purpose, `process` does the actual work of sending the reshaped data to the `NetworkImporter`.

Most implementations work like the example below.


```python
def process(self, list_of_addresses):
    """
    Accept a list of addresses, and then pass to correct instance of a NetworkImporter, 
    to update the chosen provider
    """
    provider_id = settings.provider_id
    provider = Hostingprovider.objects.get(id=provider_id)

    network_importer = NetworkImporter(provider)
    network_importer.deactivate_ips()

    return network_importer.process_addresses(list_of_addresses)

```

In this example, the `process` method on the CloudImporter object will:

1. Determine the provider to update
2. Deactivate any existing networks associated with the provider (to account for IP addresses being returned to registrars like RIPE)
3. Add, or reactivate the provider networks based on the provided IP and AS data
4. Return the results of calling the `process_addresses` method on the NetworkImporter instance, for logging, and so on.


#### Checking that importers work as expected:

We check that a cloud importer conforms to this Protocol with an assertion in the same file used to define a cloud importer. For example, in the file we define the `MicrosoftImporter`, we assert that it follows this protocol with the following line.

```
assert isinstance(MicrosoftImporter(), ImporterProtocol)
```

`CloudImporters` should also have tests, that demonstrate reshaping of fetched data. 


### Running the import from the command line

The most common way to run an import from a large provider is on a recurring cronjob, from a django management command.

An simplified management command looks like the example below.

```
python ./manage.py update_networks_in_db_google
```

When someone or script calls `update_networks_in_db_google`, the `handle` method is called, carrying out the steps we see below, exercising the three methods defined above.

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

The existing importers were created because three large providers effectively make up more than two thirds of the cloud market, and creating them was a fast way to ensure good coverage. It is posible to create new importers.

To create new importers, take the following steps:

1. Create a new importer class, satisfying the `ImporterProtocol` as described below
2. Create a management command to allow the importer to be run on a schedule.
3. Checking if any extra environment variables need to be added, to make sure an importer is able to update the correct provider in the database.
3. Add the management command to the script defined in `import_ips_for_large_providers.sh.j2`. 

```{admonition} Thinking of making a new importer?

We also have a published API with endpoints for sending updates to a provider programatically to support updating IP ranges and AS numbers. We intend to extend this API to avoid the need for creating totally new importers in future, so these can be run independently of the platform. Please contact us if you're thinking of creating an importer so we can advise the simplest way to integrate with the platform.
```

### Further Reading

**On using protocols, and composition rather than inheritance.**

- https://hynek.me/articles/python-subclassing-redux/
- https://tech.octopus.energy/news/2019/03/21/python-interfaces-a-la-go.html
- https://idego-group.com/blog/2023/02/21/we-need-to-talk-about-protocols-in-python/
