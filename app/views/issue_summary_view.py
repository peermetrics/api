import datetime

from django.core.exceptions import ValidationError
from django.db.models import Count

from ..errors import INVALID_PARAMETERS, MISSING_PARAMETERS, PMError
from ..summary_cache import cached_json
from ..utils import JSONHttpResponse
from ..models.issue import Issue, ISSUES
from .generic_view import GenericView


def _parse_iso(value):
    if value.endswith('Z'):
        value = value[:-1] + '+00:00'
    return datetime.datetime.fromisoformat(value)


class IssueSummaryView(GenericView):
    """
    Returns issue counts grouped by code. Used by the Most-common-issues chart.
    Replaces downloading all issues (73 MB+ on production) to aggregate in
    the browser.
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
            try:
                rows = (Issue.objects
                    .filter(**filters)
                    .values('code')
                    .annotate(count=Count('id'))
                    .order_by('-count'))
            except ValidationError:
                raise PMError(status=400, app_error=INVALID_PARAMETERS)

            return {'data': [
                {
                    'code': r['code'],
                    'title': ISSUES.get(r['code'], {}).get('title', r['code']),
                    'count': r['count'],
                }
                for r in rows
            ]}

        payload, _ = cached_json('issues.summary', request, compute)
        return JSONHttpResponse(payload)


class GetUserMediaSummaryView(GenericView):
    """
    Returns counts of getusermedia_error issues grouped by the error's `name`
    field inside the JSON data. Used by the GUM (getUserMedia errors) chart.
    """

    @classmethod
    def get(cls, request):
        app_id = request.GET.get('appId')
        if not app_id:
            raise PMError(status=400, app_error=MISSING_PARAMETERS)

        filters = {
            'conference__app_id': app_id,
            'code': 'getusermedia_error',
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
            from collections import Counter
            name_counter = Counter()
            message_by_name = {}

            try:
                issues = Issue.objects.filter(**filters).values_list('data', flat=True)
                for data in issues:
                    if not data:
                        continue
                    name = data.get('name') or 'Unknown'
                    name_counter[name] += 1
                    if name not in message_by_name and data.get('message'):
                        message_by_name[name] = data['message']
            except ValidationError:
                raise PMError(status=400, app_error=INVALID_PARAMETERS)

            return {
                'data': [
                    {
                        'name': name,
                        'message': message_by_name.get(name, ''),
                        'count': count,
                    }
                    for name, count in name_counter.most_common()
                ],
                'total': sum(name_counter.values()),
            }

        payload, _ = cached_json('issues.gum_summary', request, compute)
        return JSONHttpResponse(payload)
