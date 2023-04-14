from rest_framework.exceptions import NotFound


class NoSharedSecret(NotFound):
    """
    An exception raised when we try to fetch a shared secret for a provider
    but no shared secret has been set.
    """

    default_detail = "No shared secret is set. Create one by sending an empty POST request to this endpoint"
    default_code = "no_shared_secret"


class CarbonTxtFileNotFound(Exception):
    pass
