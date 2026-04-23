import datetime
from collections import Counter

from django.core.exceptions import ValidationError
from django.db.models import Case, Count, IntegerField, When

from ..errors import INVALID_PARAMETERS, MISSING_PARAMETERS, PMError
from ..summary_cache import cached_json
from ..utils import JSONHttpResponse
from ..models.connection import Connection, TYPE_OF_CONNECTIONS_ENUM
from .generic_view import GenericView


SETUP_TIME_BUCKETS = [
    {'title': '< 250 ms',       'min_ms': 0,    'max_ms': 250},
    {'title': '250 - 500 ms',   'min_ms': 250,  'max_ms': 500},
    {'title': '500 - 750 ms',   'min_ms': 500,  'max_ms': 750},
    {'title': '750 - 1000 ms',  'min_ms': 750,  'max_ms': 1000},
    {'title': '1000 - 1500 ms', 'min_ms': 1000, 'max_ms': 1500},
    {'title': '1500 - 2000 ms', 'min_ms': 1500, 'max_ms': 2000},
    {'title': '2000 - 2500 ms', 'min_ms': 2000, 'max_ms': 2500},
    {'title': '2500 - 3000 ms', 'min_ms': 2500, 'max_ms': 3000},
    {'title': '3000 - 4000 ms', 'min_ms': 3000, 'max_ms': 4000},
    {'title': '4000 - 5000 ms', 'min_ms': 4000, 'max_ms': 5000},
    {'title': '> 5000 ms',      'min_ms': 5000, 'max_ms': None},
]


def _parse_iso(value):
    if value.endswith('Z'):
        value = value[:-1] + '+00:00'
    return datetime.datetime.fromisoformat(value)


def _parse_time(value):
    if not value:
        return None
    try:
        return _parse_iso(value) if isinstance(value, str) else value
    except Exception:
        return None


def _bucket_for(ms):
    for i, b in enumerate(SETUP_TIME_BUCKETS):
        if b['max_ms'] is None:
            if ms >= b['min_ms']:
                return i
        elif b['min_ms'] <= ms < b['max_ms']:
            return i
    return None


class ConnectionSummaryView(GenericView):
    """
    Returns connection counts grouped by type — relay (TURN) vs direct.
    Replaces the Relayed-connections pie chart's client-side aggregation.
    """

    @classmethod
    def get(cls, request):
        app_id = request.GET.get('appId')
        if not app_id:
            raise PMError(status=400, app_error=MISSING_PARAMETERS)

        filters = {
            'conference__app_id': app_id,
            'is_active': True,
        }

        created_at_gte = request.GET.get('created_at_gte')
        if created_at_gte:
            try:
                filters['created_at__gte'] = _parse_iso(created_at_gte)
            except ValueError:
                raise PMError(status=400, app_error=INVALID_PARAMETERS)

        created_at_lte = request.GET.get('created_at_lte')
        if created_at_lte:
            try:
                filters['created_at__lte'] = _parse_iso(created_at_lte)
            except ValueError:
                raise PMError(status=400, app_error=INVALID_PARAMETERS)

        def compute():
            relay_code = TYPE_OF_CONNECTIONS_ENUM['relay']
            try:
                rows = (Connection.objects
                    .filter(**filters)
                    .exclude(type__isnull=True)
                    .annotate(
                        group=Case(
                            When(type=relay_code, then=1),
                            default=0,
                            output_field=IntegerField(),
                        ),
                    )
                    .values('group')
                    .annotate(count=Count('id')))
            except ValidationError:
                raise PMError(status=400, app_error=INVALID_PARAMETERS)

            counts = {0: 0, 1: 0}
            for row in rows:
                counts[row['group']] = row['count']

            return {
                'data': [
                    {'name': 'Direct', 'count': counts[0]},
                    {'name': 'Relayed', 'count': counts[1]},
                ],
            }

        payload, _ = cached_json('connections.summary', request, compute)
        return JSONHttpResponse(payload)


class ConnectionSetupTimeSummaryView(GenericView):
    """
    Returns counts of connections bucketed by initial-negotiation setup
    time (end_time - start_time on the first 'connected' negotiation
    in connection_info.negotiations).
    """

    @classmethod
    def get(cls, request):
        app_id = request.GET.get('appId')
        if not app_id:
            raise PMError(status=400, app_error=MISSING_PARAMETERS)

        filters = {
            'conference__app_id': app_id,
            'is_active': True,
        }

        created_at_gte = request.GET.get('created_at_gte')
        if created_at_gte:
            try:
                filters['created_at__gte'] = _parse_iso(created_at_gte)
            except ValueError:
                raise PMError(status=400, app_error=INVALID_PARAMETERS)

        created_at_lte = request.GET.get('created_at_lte')
        if created_at_lte:
            try:
                filters['created_at__lte'] = _parse_iso(created_at_lte)
            except ValueError:
                raise PMError(status=400, app_error=INVALID_PARAMETERS)

        def compute():
            counters = Counter()
            conferences_per_bucket = {i: set() for i in range(len(SETUP_TIME_BUCKETS))}

            try:
                rows = Connection.objects.filter(**filters).values_list(
                    'connection_info', 'conference_id'
                )
                for info, conf_id in rows:
                    if not info:
                        continue
                    negotiations = info.get('negotiations') or []
                    if not negotiations:
                        continue
                    first = negotiations[0]
                    if first.get('status') != 'connected':
                        continue
                    start = _parse_time(first.get('start_time'))
                    end = _parse_time(first.get('end_time'))
                    if not start or not end:
                        continue
                    ms = (end - start).total_seconds() * 1000
                    if ms < 0:
                        continue
                    idx = _bucket_for(ms)
                    if idx is None:
                        continue
                    counters[idx] += 1
                    conferences_per_bucket[idx].add(str(conf_id))
            except ValidationError:
                raise PMError(status=400, app_error=INVALID_PARAMETERS)

            data = []
            for i, b in enumerate(SETUP_TIME_BUCKETS):
                data.append({
                    'range': b['title'],
                    'min_ms': b['min_ms'],
                    'max_ms': b['max_ms'],
                    'count': counters.get(i, 0),
                    'conference_ids': list(conferences_per_bucket[i]),
                })
            return {'data': data}

        payload, _ = cached_json('connections.setup_time_summary', request, compute)
        return JSONHttpResponse(payload)
