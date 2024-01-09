import datetime

from django.conf import settings
from django.core.exceptions import ValidationError

from .generic_view import GenericView

from ..decorators import check_authorization, check_request_body
from ..errors import (CONFERENCE_NOT_FOUND, MISSING_PARAMETERS, CONNECTION_NOT_FOUND,
                      PARTICIPANT_NOT_FOUND, PMError, INVALID_PARAMETERS)
from ..models.conference import Conference
from ..models.connection import Connection
from ..models.generic_event import GenericEvent
from ..models.participant import Participant
from ..utils import JSONHttpResponse, serialize, validate_string, validate_positive_number


class EventView(GenericView):
    """
    Default handler for WebRTC events.

    Attrs:
        event_category: on which route the event was received, overwritten in subclasses
        require_peer_id: whether to refuse request with no peer id, overwritten in subclasses
    """
    event_category = None
    require_peer_id = None

    @staticmethod
    def query_events(event_type=None, conference=None, participant=None, filters=None):
        """Used to query and filter for GenericEvents"""

        if not isinstance(filters, dict):
            filters = dict()

        if conference:
            filters['conference'] = conference
        if participant:
            filters['participant'] = participant

        if filters.get('created_at__gt'):
            filters['created_at__gt'] = datetime.datetime.fromisoformat(filters.get('created_at__gt'))

        try:
            objs = GenericEvent.filter(**filters)

            if event_type:
                objs = objs.exclude(type=event_type[1:]) if event_type[0] == '-' else objs.filter(type=event_type)

            return objs
        except ValidationError:
            raise PMError(status=400, app_error=INVALID_PARAMETERS)

    @staticmethod
    def retrieve_events(event_type=None, conference=None, participant=None, filters=None):
        """Used to return a JSON response of a specific event query"""

        objs = EventView.query_events(event_type, conference, participant, filters)

        return JSONHttpResponse(content=serialize(objs))

    @classmethod
    def get(cls, request):
        """
        Used to retrieve events based on either conferenceId or participantId. Returns results with the event_category
        of the class.
        """

        try:
            conference = Conference.get(
                id=validate_string(request.GET.get('conferenceId')),
            ) if request.GET.get('conferenceId') else None
        except (Conference.DoesNotExist, ValidationError):
            raise PMError(status=400, app_error=CONFERENCE_NOT_FOUND)
        try:
            participant = Participant.get(
                id=validate_string(request.GET.get('participantId')),
            ) if request.GET.get('participantId') else None
        except (Participant.DoesNotExist, ValidationError):
            raise PMError(status=400, app_error=PARTICIPANT_NOT_FOUND)

        if conference or participant:

            filters = {
                'category': settings.EVENT_CATEGORIES[cls.event_category],
            }

            allowed_filters = {
                'created_at__gt': 'created_at_gt',
                'created_at__gte': 'created_at_gte',
                'created_at__lt': 'created_at_lt',
                'created_at__lte': 'created_at_lte',
            }

            for key, rkey in allowed_filters.items():
                if request.GET.get(rkey):
                    filters[key] = request.GET.get(rkey)

            return cls.retrieve_events(
                event_type=request.GET.get('type'),
                conference=conference,
                participant=participant,
                filters=filters,
            )

        raise PMError(status=400, app_error=MISSING_PARAMETERS)

    @classmethod
    @check_request_body
    @check_authorization
    def post(cls, request):
        """
        Used to retrieve events based on either conferenceId or participantId. The event is saved and based on its data
        the related session and conference are also updated.
        """

        event_type = validate_string(request.request_data.get('eventName'))
        event_data = request.request_data.get('data')
        peer_id = validate_string(request.request_data.get('peerId'))
        delta = validate_positive_number(request.request_data.get('delta', 0))

        if cls.require_peer_id and not peer_id:
            raise PMError(status=400, app_error=MISSING_PARAMETERS)

        if not event_type:
            raise PMError(status=400, app_error=MISSING_PARAMETERS)

        event = GenericEvent()

        event.participant_id = request.peer_session.participant_id
        event.conference_id = request.peer_session.conference_id
        event.session = request.peer_session
        event.app_id = request.peer_session.conference.app_id
        event.category = settings.EVENT_CATEGORIES.get(cls.event_category)
        event.type = event_type[:GenericEvent._meta.get_field('type').max_length]
        event.data = event.validate_event_body(event_data)
        event.created_at = datetime.datetime.utcnow() - datetime.timedelta(milliseconds=delta)

        event.set_connection(request.request_data)

        event.check_peer(peer_id=peer_id, request_data=request.request_data)

        event.save()

        event.process_event(now=event.created_at, request_data=request.request_data)

        content = ''
        if event.type == 'addConnection':
            content = {
                'peer_id': str(event.peer_id),
                'connection_id': str(event.connection.id),
            }

        return JSONHttpResponse(status=200, content=content)
