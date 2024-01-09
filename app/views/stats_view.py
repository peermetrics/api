import datetime
import logging

from django.conf import settings
from django.core.exceptions import ValidationError

from .event_view import EventView

from ..decorators import check_authorization, check_request_body
from ..models.generic_event import GenericEvent
from ..models.conference import Conference
from ..models.connection import Connection
from ..models.track import Track
from ..models.issue import Issue
from ..utils import JSONHttpResponse, validate_string, validate_positive_number
from ..errors import PMError, CONNECTION_NOT_FOUND, CONNECTION_ENDED

class StatsView(EventView):
    """
    Handler for stat events.

    Arguments:
        event_category: on which route the event was received, overwritten from EventView (stats in this case)
    """
    event_category = 'stats'

    @classmethod
    @check_request_body
    @check_authorization
    def post(cls, request):
        """
        Receives an HTTP request and saves the stats event in the database. Updates the event's session with connection
        type.

        :param request: the HTTP request
        """

        connection_id = validate_string(request.request_data.get('connectionId'))
        stats_data = request.request_data.get('data')
        delta = validate_positive_number(request.request_data.get('delta', 0))

        try:
            connection = Connection.get(id=connection_id)
        except (Connection.DoesNotExist, ValidationError):
            raise PMError(status=400, app_error=CONNECTION_NOT_FOUND)

        # if the connection has and end_time we wanted to stop collecting metrics for it
        # it can happen when the user calls /end-conference from their server side
        if connection.end_time:
            raise PMError(status=400, app_error=CONNECTION_ENDED)

        session = request.peer_session

        # build a new object that will be saved on the event
        data_to_save = {}
        data_to_save['connection'] = stats_data['connection']

        cls.check_connection_type(connection, stats_data['connection'])

        cls.parse_track_data(data=stats_data, new_data=data_to_save, session=session, connection=connection, delta=delta)

        if stats_data.get('remote'):
            data_to_save['remote'] = stats_data.get('remote')

            # we do not have track identifiers for remote track, 
            # so there's no reason to call parse_track_data
            # data_to_save['remote'] = {}
            # cls.parse_track_data(stats_data.get('remote'), data_to_save['remote'])

            # TODO: find a way to save stats events for the remote side for which we don't have a session/connection here
            # this might be useful when the peer is an sfu

        cls.save_event(data=data_to_save, session=session, connection=connection, delta=delta)

        Issue.check_stats(data=stats_data['connection'], session=session, connection=connection)

        return JSONHttpResponse(status=200)

    @classmethod
    def parse_track_data(cls, data, new_data, session, connection, delta=0):
        if not data or not new_data or not session or not connection:
            raise Exception('Missing arguments when calling parse_track_data')

        # for each type of track: audio, video
        # get the track object, with all directions
        for track_type, track_object in data.items():
            # we only care about these tracks
            # it will contain keys such as connection, remote
            if track_type not in ['audio', 'video']:
                continue

            # for each direction: inbound, outbound
            for direction, tracks in track_object.items():
                # tracks is an array
                for track_stats in tracks:
                    # if we have track data in the stats
                    # these are missing on firefox
                    track_info = track_stats.get('track')
                    if track_info:
                        # get the track model
                        track = cls.get_or_create_track(
                            track_id=track_info.get('trackIdentifier'),
                            direction=Track.DIRECTION_ENUM[direction],
                            kind=Track.AUDIO_VIDEO_ENUM[track_type],
                            session=session,
                            connection=connection
                        )

                        # save one event for each track stats
                        cls.save_event(data=track_stats, session=session, connection=connection, track=track, delta=delta)
                    else:
                        # if the are missing, add them to data so we save them in the DB 
                        # on the main stats event
                        new_data[track_type] = new_data.get(track_type, {})
                        new_data[track_type][direction] = new_data[track_type].get(direction, [])
                        new_data[track_type][direction].append(track_stats)

    @staticmethod
    def get_or_create_track(track_id, direction, kind, session, connection):
        try:
            track, created = Track.get_or_create(
                session=session,
                track_id=str(track_id)[:Track._meta.get_field('track_id').max_length],
                direction = direction,
                kind = kind,
            )
        except (Track.MultipleObjectsReturned):
            # TODO: this should not happen but it did once
            logging.warning('Found multiple tracks when there should have been 1')

            # just return the first one. not ideal
            track = Track.filter(
                session=session,
                track_id=str(track_id)[:Track._meta.get_field('track_id').max_length],
            )[0]
            created = False

        if not track.direction:
            track.direction = direction

        if not track.kind:
            track.kind = kind

        # make sure the track has the connection added
        if not track.connection:
            track.connection = connection

        if created:
            logging.info('Created track when we received a stats event')

        # save just in case something changed
        track.save()

        return track

    @classmethod
    def save_event(cls, data, session, connection, track=None, delta=0):
        """
        Saves a stats event. Used for each track and for the main event
        """

        if not session or not connection:
            raise Exception('Missing arguments when saving GenericEvent')

        event = GenericEvent()

        event.app = session.conference.app
        event.conference = session.conference
        event.session = session
        event.participant = session.participant
        event.peer = connection.peer
        event.connection = connection
        event.track = track
        event.type = cls.event_category
        event.category = settings.EVENT_CATEGORIES.get(cls.event_category)
        event.data = data
        event.created_at = datetime.datetime.utcnow() - datetime.timedelta(milliseconds=delta)

        event.save()

    @staticmethod
    def check_connection_type(connection, connection_object):
        local_candidate_type = connection_object.get('local', {}).get('candidateType')

        # if the connection type changed, add to the the model
        # we want to have the most updated value of type
        # to show the history of type, we have the stats events
        if connection.type != local_candidate_type:
            connection.type = Connection.TYPE_OF_CONNECTIONS_ENUM.get(local_candidate_type, None)
            connection.save()
