"""
`search` and `ordering` for list endpoints (docs/architecture/api-conventions.md).

Every list accepts the same two parameters. They are applied here, on the
queryset a domain query already built, so a domain only declares WHICH fields
are searchable and WHICH orders exist; how the text is matched and what
happens with an unknown order is decided once.

- ``search`` matches case-insensitively, as a substring, against any of the
  declared fields. Blank means no filter.
- ``ordering`` must be one of the declared keys (``"name"``, ``"-name"``, …).
  Anything else keeps the queryset's own order instead of failing: a stale
  link or a hand-typed URL still shows the list. Each key maps to a tuple of
  model fields, so a tie can be broken explicitly.

Read-side only: no DRF, no request objects (tests/unit/test_application_boundaries).
"""

from django.db.models import Q


def descending_too(orderings):
    """``{"name": ("name",)}`` plus its ``"-name"`` mirror, for symmetric whitelists."""
    expanded = dict(orderings)
    for key, fields in orderings.items():
        expanded[f"-{key}"] = tuple(
            field[1:] if field.startswith("-") else f"-{field}" for field in fields
        )
    return expanded


def search_and_order(queryset, *, search=None, ordering=None, search_fields=(), orderings=None):
    search = (search or "").strip()
    if search and search_fields:
        condition = Q()
        for field in search_fields:
            condition |= Q(**{f"{field}__icontains": search})
        queryset = queryset.filter(condition)
    fields = (orderings or {}).get((ordering or "").strip())
    if fields:
        queryset = queryset.order_by(*fields, "pk")
    return queryset
