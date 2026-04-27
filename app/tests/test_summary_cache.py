"""
Unit tests for app.summary_cache (PR #28): LocMem backend, no Redis required.
"""
from unittest.mock import patch

from django.core.cache import cache
from django.test import RequestFactory, SimpleTestCase, override_settings

from app.summary_cache import _make_key, cached_json, get_ttl


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'test-summary-cache-locmem',
        }
    }
)
class SummaryCacheTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_make_key_same_params_same_digest(self):
        rf = RequestFactory()
        a = rf.get('/', {'appId': '11111111-1111-1111-1111-111111111111'})
        b = rf.get('/', {'appId': '11111111-1111-1111-1111-111111111111'})
        self.assertEqual(_make_key('conferences.summary', a), _make_key('conferences.summary', b))

    def test_make_key_different_app_different_digest(self):
        rf = RequestFactory()
        a = rf.get('/', {'appId': '11111111-1111-1111-1111-111111111111'})
        b = rf.get('/', {'appId': '22222222-2222-2222-2222-222222222222'})
        self.assertNotEqual(_make_key('conferences.summary', a), _make_key('conferences.summary', b))

    def test_make_key_different_date_range_different_digest(self):
        rf = RequestFactory()
        a = rf.get(
            '/',
            {
                'appId': '11111111-1111-1111-1111-111111111111',
                'created_at_gte': '2026-01-01T00:00:00Z',
            },
        )
        b = rf.get(
            '/',
            {
                'appId': '11111111-1111-1111-1111-111111111111',
                'created_at_gte': '2026-02-01T00:00:00Z',
            },
        )
        self.assertNotEqual(_make_key('issues.summary', a), _make_key('issues.summary', b))

    def test_make_key_buckets_sub_minute_timestamp_precision(self):
        # The dashboard sends `new Date().toISOString()` minus 30d, which is
        # millisecond-precise. Two reloads seconds apart must collapse to the
        # same key, otherwise prewarm cannot help and Redis fills with
        # single-use entries.
        rf = RequestFactory()
        a = rf.get('/', {
            'appId': '11111111-1111-1111-1111-111111111111',
            'created_at_gte': '2026-03-28T17:13:18.382Z',
        })
        b = rf.get('/', {
            'appId': '11111111-1111-1111-1111-111111111111',
            'created_at_gte': '2026-03-28T17:13:42.001Z',
        })
        self.assertEqual(_make_key('sessions.summary', a), _make_key('sessions.summary', b))

    def test_make_key_separates_distinct_minutes(self):
        rf = RequestFactory()
        a = rf.get('/', {
            'appId': '11111111-1111-1111-1111-111111111111',
            'created_at_gte': '2026-03-28T17:13:00Z',
        })
        b = rf.get('/', {
            'appId': '11111111-1111-1111-1111-111111111111',
            'created_at_gte': '2026-03-28T17:14:00Z',
        })
        self.assertNotEqual(_make_key('sessions.summary', a), _make_key('sessions.summary', b))

    def test_make_key_ignores_query_params_not_in_cache_key_params(self):
        rf = RequestFactory()
        base = rf.get('/', {'appId': '11111111-1111-1111-1111-111111111111'})
        with_extra = rf.get(
            '/',
            {
                'appId': '11111111-1111-1111-1111-111111111111',
                'limit': '50',
                'offset': '10',
                'foo': 'bar',
            },
        )
        self.assertEqual(_make_key('sessions.summary', base), _make_key('sessions.summary', with_extra))

    def test_make_key_different_endpoint_different_digest(self):
        rf = RequestFactory()
        req = rf.get('/', {'appId': '11111111-1111-1111-1111-111111111111'})
        self.assertNotEqual(
            _make_key('conferences.summary', req),
            _make_key('issues.summary', req),
        )

    def test_cached_json_miss_then_hit_compute_once(self):
        rf = RequestFactory()
        req = rf.get('/', {'appId': '11111111-1111-1111-1111-111111111111'})
        calls = []

        def compute():
            calls.append(1)
            return {'data': [{'n': 1}]}

        p1, hit1 = cached_json('conferences.summary', req, compute)
        p2, hit2 = cached_json('conferences.summary', req, compute)

        self.assertEqual(len(calls), 1)
        self.assertFalse(hit1)
        self.assertTrue(hit2)
        self.assertEqual(p1, p2)
        self.assertEqual(p1['data'][0]['n'], 1)

    @override_settings(SUMMARY_CACHE_TTL=42)
    def test_get_ttl_reads_setting(self):
        self.assertEqual(get_ttl(), 42)

    def test_make_key_includes_conference_id_when_present(self):
        rf = RequestFactory()
        a = rf.get('/', {'appId': '11111111-1111-1111-1111-111111111111'})
        b = rf.get(
            '/',
            {
                'appId': '11111111-1111-1111-1111-111111111111',
                'conferenceId': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            },
        )
        self.assertNotEqual(_make_key('conferences.summary', a), _make_key('conferences.summary', b))

    def test_cached_json_cache_get_failure_still_returns_payload(self):
        rf = RequestFactory()
        req = rf.get('/', {'appId': '11111111-1111-1111-1111-111111111111'})

        def compute():
            return {'ok': True}

        with patch('app.summary_cache.cache.get', side_effect=RuntimeError('redis down')):
            with patch('app.summary_cache.cache.set', return_value=True):
                payload, hit = cached_json('issues.summary', req, compute)

        self.assertFalse(hit)
        self.assertEqual(payload, {'ok': True})

    def test_cached_json_cache_set_failure_still_returns_payload(self):
        rf = RequestFactory()
        req = rf.get('/', {'appId': '11111111-1111-1111-1111-111111111111'})

        def compute():
            return {'stored': False}

        with patch('app.summary_cache.cache.set', side_effect=RuntimeError('redis down')):
            payload, hit = cached_json('connections.summary', req, compute)

        self.assertFalse(hit)
        self.assertEqual(payload, {'stored': False})
