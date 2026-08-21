"""Application-level exceptions with no dependency on Django or DRF."""


class DomainError(Exception):
    """A domain invariant or business rule was violated."""


class ResourceNotFoundError(Exception):
    """A requested domain resource does not exist or has an invalid identifier."""


class AuthorizationError(Exception):
    """An authenticated actor lacks the required permission or effective scope."""
