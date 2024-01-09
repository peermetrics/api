import datetime

from django.core.exceptions import ValidationError

from ..errors import INVALID_PARAMETERS, ISSUE_NOT_FOUND, MISSING_PARAMETERS, PMError
from ..utils import JSONHttpResponse, serialize
from ..models.issue import Issue
from .generic_view import GenericView

class IssueView(GenericView):
    """
    View for handling the conference objects.
    """

    @classmethod
    def filter(cls, request):
        """
        Method for retrieving connections based on filters. Returns 400 if no filters are supplied.
        """
        filters = {}
        allowed_filters = {
            'conference__app_id': 'appId',
            'conference_id': 'conferenceId',
            'participant_id': 'participantId',
            'created_at__gt': 'created_at_gt',
            'created_at__gte': 'created_at_gte',
            'created_at__lt': 'created_at_lt',
            'created_at__lte': 'created_at_lte',
        }

        for key, rkey in allowed_filters.items():
            if request.GET.get(rkey):
                filters[key] = request.GET.get(rkey)

        if not filters:
            raise PMError(status=400, app_error=MISSING_PARAMETERS)

        if filters.get('created_at__gt'):
            filters['created_at__gt'] = datetime.datetime.fromisoformat(filters.get('created_at__gt'))

        try:
            objs = Issue.filter(**filters)
        except ValidationError:
            raise PMError(status=400, app_error=INVALID_PARAMETERS)

        return JSONHttpResponse(
            content=serialize(
                objs=objs,
                properties=['title', 'explanation']
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
            obj = Issue.get(id=pk)
        except Issue.DoesNotExist:
            raise PMError(status=400, app_error=ISSUE_NOT_FOUND)

        return JSONHttpResponse(
            content=serialize(
                [obj],
                return_single_object=True,
            ),
        )
