"""
Short-TTL Redis cache for dashboard summary endpoints.

The summary endpoints run SQL aggregations that are fast enough on their own
but get called by every dashboard page load. Cache the computed JSON for
~60 seconds so concurrent viewers share the same roll-up.

Keys are derived from the endpoint name + all request filters, so different
date ranges / apps get independent entries. TTL-only — no explicit
invalidation — because the data is strictly additive (new conferences,
sessions, issues arrive over time) and a sub-minute staleness window is
acceptable for a dashboard.
"""
import hashlib
import json
import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 60
KEY_PREFIX = 'summary'

# The query-string params that factor into the cache key for each endpoint.
# Anything not listed here is ignored (e.g. trailing slashes, user agent, etc).
CACHE_KEY_PARAMS = (
    'appId',
    'created_at_gte',
    'created_at_lte',
    'conferenceId',
    'participantId',
)


def _make_key(endpoint, request):
    parts = [endpoint]
    for name in CACHE_KEY_PARAMS:
        val = request.GET.get(name)
        if val:
            parts.append(f'{name}={val}')
    raw = '|'.join(parts)
    # Keep key short but unique; include a readable prefix for ops visibility.
    digest = hashlib.sha1(raw.encode()).hexdigest()[:16]
    return f'{KEY_PREFIX}:{endpoint}:{digest}'


def get_ttl():
    return getattr(settings, 'SUMMARY_CACHE_TTL', DEFAULT_TTL_SECONDS)


def cached_json(endpoint, request, compute):
    """
    Returns (payload_dict, was_cached_bool).

    `compute` is called only on cache miss and must return the JSON-serializable
    dict the endpoint would have returned.
    """
    key = _make_key(endpoint, request)
    try:
        cached = cache.get(key)
    except Exception as e:
        logger.warning('summary cache get failed for %s: %s', key, e)
        cached = None

    if cached is not None:
        return cached, True

    payload = compute()
    try:
        cache.set(key, payload, timeout=get_ttl())
    except Exception as e:
        logger.warning('summary cache set failed for %s: %s', key, e)
    return payload, False
