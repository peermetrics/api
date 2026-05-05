import datetime

from django.core.exceptions import ValidationError
from django.db.models import Case, Count, IntegerField, When

from ..errors import INVALID_PARAMETERS, MISSING_PARAMETERS, PMError
from ..summary_cache import cached_json
from ..utils import JSONHttpResponse
from ..models.conference import Conference
from .generic_view import GenericView


BUCKETS = [
    {'title': '< 1 m',    'min_sec': 0,    'max_sec': 60},
    {'title': '1 - 3 m',  'min_sec': 60,   'max_sec': 180},
    {'title': '3 - 5 m',  'min_sec': 180,  'max_sec': 300},
    {'title': '5 - 10 m', 'min_sec': 300,  'max_sec': 600},
    {'title': '10 - 15 m','min_sec': 600,  'max_sec': 900},
    {'title': '15 - 20 m','min_sec': 900,  'max_sec': 1200},
    {'title': '20 - 25 m','min_sec': 1200, 'max_sec': 1500},
    {'title': '25 - 30 m','min_sec': 1500, 'max_sec': 1800},
    {'title': '30 - 40 m','min_sec': 1800, 'max_sec': 2400},
    {'title': '40 - 50 m','min_sec': 2400, 'max_sec': 3000},
    {'title': '50 - 60 m','min_sec': 3000, 'max_sec': 3600},
    {'title': '> 60 m',   'min_sec': 3600, 'max_sec': None},
]


def _parse_iso(value):
    if value.endswith('Z'):
        value = value[:-1] + '+00:00'
    return datetime.datetime.fromisoformat(value)


class ConferenceDurationSummaryView(GenericView):
    """Returns conference count bucketed by duration range."""

    @classmethod
    def get(cls, request):
        app_id = request.GET.get('appId')
        if not app_id:
            raise PMError(status=400, app_error=MISSING_PARAMETERS)

        filters = {'app_id': app_id, 'is_active': True}

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
            whens = []
            for i, b in enumerate(BUCKETS):
                lo, hi = b['min_sec'], b['max_sec']
                if hi is None:
                    whens.append(When(duration__gte=lo, then=i))
                elif lo == 0:
                    whens.append(When(duration__lt=hi, then=i))
                else:
                    whens.append(When(duration__gte=lo, duration__lt=hi, then=i))

            try:
                rows = (Conference.objects
                    .filter(**filters)
                    .annotate(bucket=Case(*whens, output_field=IntegerField()))
                    .values('bucket')
                    .annotate(count=Count('id'))
                    .order_by('bucket'))
            except ValidationError:
                raise PMError(status=400, app_error=INVALID_PARAMETERS)

            counts_by_bucket = {r['bucket']: r['count'] for r in rows if r['bucket'] is not None}
            return {'data': [
                {
                    'range': b['title'],
                    'min_sec': b['min_sec'],
                    'max_sec': b['max_sec'],
                    'count': counts_by_bucket.get(i, 0),
                }
                for i, b in enumerate(BUCKETS)
            ]}

        payload, _ = cached_json('conferences.duration_summary', request, compute)
        return JSONHttpResponse(payload)
