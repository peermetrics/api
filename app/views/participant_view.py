from django.core.exceptions import ValidationError

from ..errors import (INVALID_PARAMETERS, PARTICIPANT_NOT_FOUND,
                      MISSING_PARAMETERS, PMError)
from ..utils import JSONHttpResponse, serialize
from ..models.participant import Participant
from .generic_view import GenericView

# from server_timing.middleware import timed, timed_wrapper

class ParticipantsView(GenericView):
    """
    View for handling the participant objects.
    """
    model = Participant

    @classmethod
    def filter(cls, request):
        """
        Method for retrieving participants based on filters. Returns 400 if no filters are supplied.
        """

        filters = {}
        allowed_filters = {
            'app_id': 'appId',
            'conferences__id': 'conferenceId',
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

        try:
            objs = Participant.filter(**filters)
        except ValidationError:
            raise PMError(status=400, app_error=INVALID_PARAMETERS)

        return JSONHttpResponse(
            content=serialize(
                objs=objs,
            ),
        )

    @classmethod
    def get(cls, request, pk=None):
        """
        Get method. Returns the object if the user has access to it. Calls filter if no id is supplied.
        """
        if not pk:
            return cls.filter(request)

        try:
            obj = Participant.get(id=pk)
        except Participant.DoesNotExist:
            raise PMError(status=400, app_error=PARTICIPANT_NOT_FOUND)

        return JSONHttpResponse(
            content=serialize(
                [obj],
                return_single_object=True,
            ),
        )
