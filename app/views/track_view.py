import datetime

from django.core.exceptions import ValidationError
from django.conf import settings

from ..errors import (TRACK_NOT_FOUND, PMError, CONNECTION_NOT_FOUND)
from ..utils import JSONHttpResponse, serialize, validate_string, validate_positive_number
from .generic_view import GenericView
from ..decorators import check_authorization, check_request_body
from ..models.track import Track
from ..models.connection import Connection
from ..models.generic_event import GenericEvent


class TracksView(GenericView):
    """
    View for handling the track objects.
    """

    @classmethod
    def save_event(cls, event_type, data, session, connection=None, track=None, delta=0):
        """
        Saves an event.
        """
        event = GenericEvent()

        event.app = session.conference.app
        event.conference = session.conference
        event.session = session
        event.participant = session.participant
        event.peer = connection.peer if connection is not None else None
        event.connection = connection
        event.track = track
        event.type = event_type
        event.category = settings.EVENT_CATEGORIES.get('track')
        event.data = data
        event.created_at = datetime.datetime.utcnow() - datetime.timedelta(milliseconds=delta)

        event.save()

    @classmethod
    @check_request_body
    @check_authorization
    def post(cls, request):
        """
        Post method.
        {
            "event": "ontrack",
            "peerId": "1605445711866",
            "connectionId": "03c3cea3-16bb-4d92-86c9-1e7afd42ee13",
            "trackId": "f2c86ea9-d564-4825-bba4-1bf00f19b457",
            "data": {}
        }
        """

        event_type = validate_string(request.request_data.get('event'))
        track_id = validate_string(request.request_data.get('trackId'))
        connection_id = validate_string(request.request_data.get('connectionId'))
        event_data = request.request_data.get('data')
        delta = validate_positive_number(request.request_data.get('delta', 0))

        try:
            connection = Connection.get(id=connection_id)
        except (Connection.DoesNotExist, ValidationError):
            raise PMError(status=400, app_error=CONNECTION_NOT_FOUND)

        # make sure we respect the max_length
        # do this here so the query bellow also uses the shortened track id
        track_id = track_id[:Track._meta.get_field('track_id').max_length]

        try:
            track = Track.get(connection__id=connection.id, track_id=track_id)

            cls.log.warning('Found a track on post', labels={'track_id': track_id, 'connection_id': connection_id})
        except Track.DoesNotExist:
            track = Track(
                connection=connection,
                session=request.peer_session,
                track_id=track_id,
                kind=Track.AUDIO_VIDEO_ENUM.get(event_data.get('kind')),
                direction=Track.DIRECTION_ENUM.get(event_data.get('direction', 'inbound')),
                # make sure the label respects the max_lengtgh on the DB field
                label=event_data.get('label')[:Track._meta.get_field('label').max_length]
            )
            track.track_info['capabilities'] = event_data.get('capabilities')
            track.track_info['settings'] = event_data.get('settings')
            track.track_info['enabled'] = event_data.get('enabled')
            track.track_info['readyState'] = event_data.get('readyState')
            track.track_info['contentHint'] = event_data.get('contentHint')
            track.track_info['constraints'].append(event_data.get('constraints'))
            track.save()

        cls.save_event(
            event_type=event_type, data=event_data, session=request.peer_session,
            connection=connection, track=track, delta=delta,
        )

        return JSONHttpResponse(
            content=serialize(
                [track],
                return_single_object=True,
            ),
        )

    @classmethod
    @check_request_body
    @check_authorization
    def put(cls, request):
        """
        Put method.
        {
            "event": "unmute",
            "trackId": "11b28b01-3903-4e60-be2e-b4c3f5443e09",
            "data": {}
        }
        """

        event_type = validate_string(request.request_data.get('event'))
        track_id = validate_string(request.request_data.get('trackId'))
        event_data = request.request_data.get('data')
        delta = validate_positive_number(request.request_data.get('delta', 0))

        track_id = track_id[:Track._meta.get_field('track_id').max_length]

        try:
            try:
                track = Track.objects.get(track_id=track_id, session__id=request.peer_session.id)
                
            except Track.MultipleObjectsReturned:
                cls.log.warning('Found multiple tracks with the same track_id', meta={'data': event_data}, labels={'track_id': track_id})

                # take the first one
                track = Track.objects.filter(track_id=track_id, session__id=request.peer_session.id)[0]

            if event_type == 'unmute':
                track.track_info['muted'] = False
            elif event_type == 'mute':
                track.track_info['muted'] = True
            elif event_type == 'ended':
                track.track_info['ended'] = True
                track.track_info['readyState'] = 'ended'

            track.save()

            cls.save_event(
                event_type=event_type, data=event_data, session=request.peer_session,
                connection=track.connection, track=track, delta=delta,
            )

        except (Track.DoesNotExist, ValidationError):
            cls.log.warning('Could not find track on PUT', meta={'data': event_data}, labels={'track_id': track_id})

            cls.save_event(
                event_type=event_type, data=event_data, session=request.peer_session, delta=delta,
            )
            raise PMError(status=400, app_error=TRACK_NOT_FOUND)

        return JSONHttpResponse(
            status=200,
            content=serialize(
                [track],
                return_single_object=True,
            ),
        )
