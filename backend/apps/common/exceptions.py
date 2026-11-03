"""Application-level exceptions with no dependency on Django or DRF."""


class DomainError(Exception):
    """A domain invariant or business rule was violated."""


class FieldValidationError(DomainError):
    """
    A business rule rejected specific input fields.

    ``errors`` maps a field name to its messages, so the API can answer with the
    same per-field shape DRF uses (``{"password": ["...", "..."]}``) and the
    client can show each message next to its field (docs/ux-ui.md, MC2).
    """

    def __init__(self, errors):
        self.errors = {field: list(messages) for field, messages in errors.items()}
        messages = [text for field_messages in self.errors.values() for text in field_messages]
        super().__init__(" ".join(messages))


class ResourceNotFoundError(Exception):
    """A requested domain resource does not exist or has an invalid identifier."""


class AuthorizationError(Exception):
    """An authenticated actor lacks the required permission or effective scope."""
