import datetime

from django.db import transaction
from django.conf import settings

from .connection_event_view import ConnectionEventView
from ..errors import PMError, METHOD_NOT_ALLOWED, MISSING_PARAMETERS
from ..decorators import check_authorization, check_request_body
from ..utils import validate_string, JSONHttpResponse, validate_positive_number
from ..models.generic_event import GenericEvent

from ..logger import log

class ConnectionEventBatchView(ConnectionEventView):
    """
    Handler for a batch of connection WebRTC events.
    """

    @classmethod
    @check_request_body
    @check_authorization
    def post(cls, request):
        """
        Used to retrieve a larger number of connection events based on either conferenceId or participantId. The events
        are saved and based on their data the related session and conference are also updated.
        """
        events = request.request_data.get('data')
        delta = validate_positive_number(request.request_data.get('delta', 0))
        now = datetime.datetime.utcnow() - datetime.timedelta(milliseconds=delta)

        with transaction.atomic():
            for event_body in events:
                event_type = validate_string(event_body.get('eventName'))
                event_data = event_body.get('data')
                peer_id = validate_string(event_body.get('peerId'))
                delta = validate_positive_number(event_body.get('delta', 0))

                if (cls.require_peer_id and not peer_id) or not event_type:
                    log.warning('Invalid connection in batching: {}, {}'.format(peer_id, event_type))
                    # do not save this event
                    continue
                    # raise PMError(status=400, app_error=MISSING_PARAMETERS)

                event = GenericEvent()

                event.participant_id = request.peer_session.participant_id
                event.conference_id = request.peer_session.conference_id
                event.session = request.peer_session
                event.app_id = request.peer_session.conference.app_id
                event.category = settings.EVENT_CATEGORIES.get(cls.event_category)
                event.type = event_type[:GenericEvent._meta.get_field('type').max_length]
                event.data = event.validate_event_body(event_data)
                event.created_at = now - datetime.timedelta(milliseconds=delta)

                log.warning(delta)
                # log.warning(event.created_at)

                event.set_connection(event_body)

                event.check_peer(peer_id=peer_id, request_data=event_body)

                event.save()

                event.process_event(request_data=event_body, now=event.created_at)

        return JSONHttpResponse(status=200)

    @classmethod
    def get(cls, request):
        raise PMError(status=405, app_error=METHOD_NOT_ALLOWED)
