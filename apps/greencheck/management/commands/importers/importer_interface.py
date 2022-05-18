import abc
import ipaddress
import re


class ImporterInterface(metaclass=abc.ABCMeta):
    @classmethod
    def __init__(cls, subclass):
        list_of_addresses = subclass.fetch_data()

        process_addresses(list_of_addresses)

    @classmethod
    def __subclasshook__(cls, subclass):
        """
        Override subclasshook to redefine what requirements there are to be
        considered a subclass of this interface.
        Usage:      issubclass(subclass, superclass)
        Example:    issubclass(ProviderNameImporter, ImporterInterface) # True or False
        """
        return (
            hasattr(subclass, "fetch_data")
            and callable(subclass.fetch_data)
            or NotImplemented
        )

    @classmethod
    def process_addresses(list_of_addresses):
        # Determine the type of address (IPv4, IPv6 or ASN)for address in list_of_addresses:
        try:
            if re.search("(AS)[0-9]{4}$", address):
                # Address is ASN
                save_asn(address)
            elif isinstance(
                ipaddress.ip_network(address),
                (ipaddress.IPv4Network, ipaddress.IPv6Network),
            ):
                # Address is IPv4 or IPv6
                save_ip(address)
        except ValueError:
            logger.exception(
                "Value has invalid structure. Must be IPv4 or IPv6 with subnetmask (101.102.103.104/27) or AS number (AS1234)."
            )
            # raise ValueError("Value has invalid structure. Must be IPv4 or IPv6 with subnetmask (101.102.103.104/27) or AS number (AS1234).")
        except Exception:
            logger.exception("Something really unexpected happened. Aborting")

    @classmethod
    def save_asn(address: str):
        hoster = Hostingprovider.objects.get(
            pk=settings.AZURE_PROVIDER_ID
        )  # TODO: Need a way to fetch the ID from subclasses here

        gc_asn, created = GreencheckASN.objects.update_or_create(
            active=True, asn=int(address.replace("AS", "")), hostingprovider=hoster
        )
        gc_asn.save()  # Save the newly created or updated object

        if created:
            # Only log and return when a new object was created
            logger.debug(gc_asn)
            return gc_asn

    @classmethod
    def save_ip(address: str):
        # Convert to IPv4 network with it's respective range
        network = ipaddress.ip_network(address)
        hoster = Hostingprovider.objects.get(
            pk=settings.AZURE_PROVIDER_ID
        )  # TODO: Need a way to fetch the ID from subclasses here

        gc_ip, created = GreencheckIp.objects.update_or_create(
            active=True, ip_start=network[1], ip_end=network[-1], hostingprovider=hoster
        )
        gc_ip.save()  # Save the newly created or updated object

        if created:
            # Only log and return when a new object was created
            logger.debug(gc_ip)
            return gc_ip

    @abc.abstractmethod
    def fetch_data() -> list:
        raise NotImplementedError
