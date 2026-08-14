"""Expected application failures with transport-independent semantics."""


class ApplicationError(Exception):
    """Base class for failures that may be safely mapped at the API boundary."""


class InvalidRequestError(ApplicationError):
    """The caller supplied a value that cannot be processed safely."""


class UpstreamTimeoutError(ApplicationError):
    """The World Bank API exceeded the configured deadline."""


class UpstreamConnectionError(ApplicationError):
    """The World Bank API could not be reached."""


class UpstreamResponseError(ApplicationError):
    """The World Bank API returned an unsuccessful or malformed response."""


class ForecastUnavailableError(ApplicationError):
    """The selected observations cannot produce a responsible forecast."""
