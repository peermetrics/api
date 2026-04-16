import datetime
from collections import defaultdict

from django.core.exceptions import ValidationError
from django.db.models import Case, CharField, Count, Exists, OuterRef, Value, When
from django.db.models.functions import TruncDate

from ..errors import INVALID_PARAMETERS, MISSING_PARAMETERS, PMError
from ..utils import JSONHttpResponse
from ..models.conference import Conference
from ..models.issue import Issue
from .generic_view import GenericView


def _parse_iso(value):
    # Python 3.8 fromisoformat doesn't accept the Z suffix that JS toISOString produces.
    if value.endswith('Z'):
        value = value[:-1] + '+00:00'
    return datetime.datetime.fromisoformat(value)


class ConferenceSummaryView(GenericView):
    """
    Returns conference counts grouped by day, with each day's conferences
    bucketed into success/warning/error/ongoing. Replaces the pattern of
    downloading all conferences to the browser and aggregating client-side.
    """

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

        try:
            rows = (Conference.objects
                .filter(**filters)
                .annotate(
                    day=TruncDate('created_at'),
                    has_error=Exists(
                        Issue.objects.filter(conference=OuterRef('pk'), type='e', is_active=True)
                    ),
                    has_warning=Exists(
                        Issue.objects.filter(conference=OuterRef('pk'), type='w', is_active=True)
                    ),
                )
                .annotate(
                    status=Case(
                        When(ongoing=True, then=Value('ongoing')),
                        When(has_error=True, then=Value('error')),
                        When(has_warning=True, then=Value('warning')),
                        default=Value('success'),
                        output_field=CharField(),
                    ),
                )
                .values('day', 'status')
                .annotate(count=Count('id'))
                .order_by('day'))
        except ValidationError:
            raise PMError(status=400, app_error=INVALID_PARAMETERS)

        buckets = defaultdict(lambda: {'success': 0, 'warning': 0, 'error': 0, 'ongoing': 0})
        for row in rows:
            day_key = row['day'].isoformat() if row['day'] else None
            buckets[day_key][row['status']] = row['count']

        data = [
            {
                'date': day,
                'success': counts['success'],
                'warning': counts['warning'],
                'error': counts['error'],
                'ongoing': counts['ongoing'],
                'total': counts['success'] + counts['warning'] + counts['error'] + counts['ongoing'],
            }
            for day, counts in sorted(buckets.items(), key=lambda x: x[0] or '')
        ]

        return JSONHttpResponse({'data': data})
