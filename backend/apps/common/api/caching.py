"""
Opt-in HTTP caching for read endpoints, shared across apps.

Nothing in this codebase sent ``Cache-Control``/``ETag`` before this: every
response was recomputed and retransmitted in full, always, even for catalogs
(levels, sections, cycles, subjects, campuses) that change rarely. This is one
small, reusable mixin applied via a class attribute, not a decorator copied
onto each view.

The 304 short-circuit is handled here, not via Django's
``ConditionalGetMiddleware``: that middleware stamps an ETag onto every GET
response app-wide the moment it is installed (its own default behavior,
unrelated to whether a view opted in), which would undo the point of this
being opt-in. Keeping it local to the mixin means only a view that sets
``cache_seconds`` is affected.
"""

import hashlib

from django.http import HttpResponseNotModified
from django.utils.cache import patch_cache_control


class CacheableListMixin:
    """
    Adds ``Cache-Control`` and ``ETag`` to a successful GET response, and
    answers a matching conditional GET (``If-None-Match``) with 304.

    ``cache_seconds`` defaults to ``None`` (no change in behavior) so opting a
    view in is a single explicit line. Only apply this to a list that a
    browser can safely serve stale for that long -- anything that mutates on
    (almost) every request, or that must never be cached (auth/session,
    per-request-sensitive data), must not set it.

    ``private`` because these responses are scoped to the authenticated
    user's institution/permissions: a shared cache (a CDN, a proxy) caching
    them for someone else would leak another institution's catalogue.
    """

    cache_seconds = None

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if self.cache_seconds is None or response.status_code != 200:
            return response

        # ETag needs the actual bytes; DRF's Response defers rendering to
        # Django's response cycle, so it is forced here rather than trusted
        # to have happened already. `render()` is a no-op on a second call.
        response.render()
        etag = f'"{hashlib.sha256(response.content).hexdigest()}"'
        patch_cache_control(response, private=True, max_age=self.cache_seconds)

        if request.META.get("HTTP_IF_NONE_MATCH") == etag:
            not_modified = HttpResponseNotModified()
            not_modified["ETag"] = etag
            not_modified["Cache-Control"] = response["Cache-Control"]
            return not_modified

        response["ETag"] = etag
        return response
