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

# Params whose ISO timestamps should be truncated to the minute before hashing,
# so that the dashboard's millisecond-precise `now - 30d` doesn't produce a
# unique cache key per page load. Bucketing means two requests in the same
# wall-clock minute share an entry; correctness still holds because the cache
# entry's own TTL bounds staleness regardless of bucket size.
BUCKETED_PARAMS = ('created_at_gte', 'created_at_lte')


def _bucket_minute(value):
    # ISO 8601: 2026-03-28T17:13:18.382Z -> 2026-03-28T17:13Z (first 16 chars
    # are YYYY-MM-DDTHH:MM). Anything that doesn't match the layout is
    # passed through unchanged so the key still differentiates malformed input.
    if not value or len(value) < 16 or value[10] != 'T' or value[13] != ':':
        return value
    return value[:16] + 'Z'


def _make_key(endpoint, request):
    parts = [endpoint]
    for name in CACHE_KEY_PARAMS:
        val = request.GET.get(name)
        if val:
            if name in BUCKETED_PARAMS:
                val = _bucket_minute(val)
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
