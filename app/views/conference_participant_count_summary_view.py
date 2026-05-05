import datetime
from collections import Counter

from django.core.exceptions import ValidationError
from ..conference_query import PARTICIPANTS_COUNT_ANNOTATION
from ..errors import INVALID_PARAMETERS, MISSING_PARAMETERS, PMError
from ..summary_cache import cached_json
from ..utils import JSONHttpResponse
from ..models.conference import Conference
from .generic_view import GenericView


def _parse_iso(value):
    if value.endswith('Z'):
        value = value[:-1] + '+00:00'
    return datetime.datetime.fromisoformat(value)


class ConferenceParticipantCountSummaryView(GenericView):
    """
    Returns the distribution of conferences grouped by how many participants
    they had. Used by the Number-of-participants pie chart.
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

        def compute():
            try:
                per_conf = (Conference.objects
                    .filter(**filters)
                    .annotate(participants_count=PARTICIPANTS_COUNT_ANNOTATION)
                    .values_list('participants_count', flat=True))
            except ValidationError:
                raise PMError(status=400, app_error=INVALID_PARAMETERS)

            distribution = Counter()
            total = 0
            for count in per_conf:
                distribution[count or 0] += 1
                total += 1

            return {
                'data': [
                    {'participants': n, 'conferences': c}
                    for n, c in sorted(distribution.items())
                ],
                'total_conferences': total,
            }

        payload, _ = cached_json('conferences.participant_count_summary', request, compute)
        return JSONHttpResponse(payload)
