import logging
from typing import List, Protocol, Tuple, Union, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
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
