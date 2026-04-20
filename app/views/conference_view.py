import datetime

from django.core.exceptions import ValidationError
from django.db.models import Count, Exists, IntegerField, OuterRef, Subquery

from ..errors import (INVALID_PARAMETERS, CONFERENCE_NOT_FOUND,
                      MISSING_PARAMETERS, PMError)
from ..utils import JSONHttpResponse, serialize, paginate_and_serialize
from ..models.conference import Conference
from ..models.issue import Issue
from ..models.participant import Participant
from .generic_view import GenericView

class ConferencesView(GenericView):
    """
    View for handling the conference objects.
    """

    @classmethod
    def filter(cls, request):
        """
        Method for retrieving conferences based on filters. Checks if objects are too old to be retrieved based on the
        subscription of the user. Returns 400 if no filters are supplied.
        """
        filters = {}
        allowed_filters = {
            'app_id': 'appId',
            'participants': 'participantId',
            'created_at__gt': 'created_at_gt',
            'created_at__gte': 'created_at_gte',
            'created_at__lt': 'created_at_lt',
            'created_at__lte': 'created_at_lte',
            'duration__gte': 'duration_gte',
            'duration__lt': 'duration_lt',
            'issues__code': 'issue_code',
        }

        for key, rkey in allowed_filters.items():
            if request.GET.get(rkey):
                filters[key] = request.GET.get(rkey)

        ids_param = request.GET.get('conference_ids')
        if ids_param:
            ids = [i for i in ids_param.split(',') if i]
            if ids:
                filters['id__in'] = ids

        if not filters:
            raise PMError(status=400, app_error=MISSING_PARAMETERS)

        if filters.get('created_at__gt'):
            filters['created_at__gt'] = datetime.datetime.fromisoformat(filters.get('created_at__gt'))

        try:
            objs = Conference.filter(**filters).annotate(
                has_errors=Exists(
                    Issue.objects.filter(conference=OuterRef('pk'), type='e', is_active=True)
                ),
                has_warnings=Exists(
                    Issue.objects.filter(conference=OuterRef('pk'), type='w', is_active=True)
                ),
                participants_count=Subquery(
                    Participant.objects.filter(
                        conferences=OuterRef('pk'),
                        is_active=True,
                    ).order_by().values('conferences').annotate(
                        cnt=Count('id', distinct=True)
                    ).values('cnt')[:1],
                    output_field=IntegerField(),
                ),
            )
        except ValidationError:
            raise PMError(status=400, app_error=INVALID_PARAMETERS)

        return JSONHttpResponse(
            content=paginate_and_serialize(
                request, objs,
                properties=['has_errors', 'has_warnings', 'participants_count'],
            ),
        )

    @classmethod
    def get(cls, request, pk=None):
        """
        Get method. Returns the object if the user has access to it and it is not older than the user's retention days.
        Calls filter if no id is supplied.
        """
        if not pk:
            return cls.filter(request)

        try:
            obj = Conference.get(id=pk)
        except Conference.DoesNotExist:
            raise PMError(status=400, app_error=CONFERENCE_NOT_FOUND)

        return JSONHttpResponse(
            content=serialize(
                [obj],
                expand_fields=('participants', 'issues'),
                return_single_object=True,
            ),
        )
