import datetime
import uuid

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.core.exceptions import ValidationError

from .app import App
from .basemodel import BaseModel
from ..errors import PMError, INVALID_PARAMETERS, PARTICIPANT_NOT_FOUND, PARTICIPANT_EQUAL_PEER, CONNECTION_NOT_FOUND
from .participant import Participant
from .connection import Connection, CONNECTION_STATE_ENUM
from .track import Track
from ..utils import validate_string
from .issue import Issue


class GenericEvent(BaseModel):
    """
    A model for all user events

    Fields:
        id: ID from db, UUID
        conference: the conference linked to the event
        participant: the participant linked to the event
        peer: the other participant linked to the event
        session: the session linked to the event
        app: the app linked to the event
        type: the event type, received in request
        category: the event category, set based on the route it is received on
        data: the data of the event
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    conference = models.ForeignKey('Conference', on_delete=models.CASCADE, null=False, related_name='events')
    participant = models.ForeignKey('Participant', on_delete=models.CASCADE, null=False, related_name='events')
    peer = models.ForeignKey(
        'Participant', on_delete=models.CASCADE, null=True, blank=True, related_name='events_where_peer',
    )
    session = models.ForeignKey('Session', on_delete=models.CASCADE, null=False, related_name='events')
    connection = models.ForeignKey('Connection', on_delete=models.CASCADE, null=True, blank=True, related_name='events')
    track = models.ForeignKey('Track', on_delete=models.CASCADE, null=True, blank=True, related_name='events')
    app = models.ForeignKey(App, on_delete=models.CASCADE, null=False, related_name='events')
    type = models.CharField(null=False, max_length=32)
    category = models.CharField(
        max_length=1,
        choices=tuple([(settings.EVENT_CATEGORIES[key], key) for key in settings.EVENT_CATEGORIES.keys()]),
    )
    data = JSONField(null=True, blank=True, default=dict)
    created_at = models.DateTimeField(default=datetime.datetime.utcnow)
    is_active = models.BooleanField(default=True)

    def alter_event_body(self, event_data):
        if event_data and self.type == 'onicecandidate':
            allowed_keys = [
                'address', 'candidate', 'component', 'foundation', 'port',
                'priority', 'protocol', 'relatedAddress', 'relatedPort',
                'sdpMLineIndex', 'sdpMid', 'tcpType', 'type', 'usernameFragment',
            ]
            return {key: event_data[key] for key in allowed_keys if event_data.get(key) is not None}

        return event_data

    def validate_event_body(self, event_data):
        if (
            self.type == 'oniceconnectionstatechange'
            and event_data not in ['new', 'checking', 'connected', 'completed', 'failed', 'disconnected', 'closed']
        ):
            raise PMError(status=400, app_error=INVALID_PARAMETERS)

        if (
            self.type == 'onsignalingstatechange'
            and event_data.get('signalingState') not in [
                'stable', 'have-local-offer', 'have-remote-offer',
                'have-local-pranswer', 'have-remote-pranswer', 'closed',
            ]
        ):
            raise PMError(status=400, app_error=INVALID_PARAMETERS)

        if (
            self.type == 'onicegatheringstatechange'
            and event_data not in ['new', 'gathering', 'complete']
        ):
            raise PMError(status=400, app_error=INVALID_PARAMETERS)

        if (
            self.type == 'icecandidateerror'
            and not (
                (isinstance(event_data, int) or isinstance(event_data, float))
                and 300 < event_data < 799
            )
        ):
            raise PMError(status=400, app_error=INVALID_PARAMETERS)

        if (
            self.type == 'connectionstatechange'
            and event_data not in ['new', 'connecting', 'connected', 'disconnected', 'failed', 'closed']
        ):
            raise PMError(status=400, app_error=INVALID_PARAMETERS)

        if (
            self.type == 'negotiationneeded'
            and event_data is not None
        ):
            raise PMError(status=400, app_error=INVALID_PARAMETERS)

        if (
            self.type == 'datachannel'
            and event_data is not None
        ):
            raise PMError(status=400, app_error=INVALID_PARAMETERS)

        if (
            self.type == 'stats'
            and (
                not isinstance(event_data, dict)
                # the four tags are mandatory but others can exist i.e. parsedStats
                or any([elem not in event_data.keys() for elem in ['audio', 'connection', 'video', 'remote']])
            )
        ):
            raise PMError(status=400, app_error=INVALID_PARAMETERS)

        return self.alter_event_body(event_data)

    def check_peer(self, peer_id, request_data):
        if peer_id:
            if self.type == 'addConnection':
                participant, created = Participant.get_or_create(
                    participant_id=peer_id,
                    is_sfu=bool(request_data.get('isSfu')),
                    app_id=self.app_id
                )

                if participant.id == self.participant_id:
                    raise PMError(status=400, app_error=PARTICIPANT_EQUAL_PEER)

                self.conference.participants.add(participant)

                peer_name = validate_string(request_data.get('peerName'))
                if isinstance(peer_name, str):
                    participant.participant_name = peer_name
                    participant.save()
            else:
                try:
                    participant = Participant.get(id=peer_id, conferences__id=self.conference_id)
                except (Participant.DoesNotExist, ValidationError):
                    raise PMError(status=400, app_error=PARTICIPANT_NOT_FOUND)

                if participant.id == self.participant_id:
                    raise PMError(status=400, app_error=PARTICIPANT_EQUAL_PEER)

            self.peer = participant
        else:
            self.peer = None

    def set_connection(self, request_data):
        connection_id = validate_string(request_data.get('connectionId'))
        if not connection_id:
            return

        try:
            self.connection = Connection.get(id=connection_id)
        except (Connection.DoesNotExist, ValidationError):
            raise PMError(status=400, app_error=CONNECTION_NOT_FOUND)

    def process_event(self, now, request_data):

        if self.type == 'getUserMedia':
            data = request_data.get('data', {})

            # create audio tracks, if needed
            # we can assume these are outbound tracks
            Track.create_tracks(data.get('audio'), session=self.session, direction='outbound')

            # create video tracks, if needed
            # we can assume these are outbound tracks
            Track.create_tracks(data.get('video'), session=self.session, direction='outbound')

            if data.get('error'):
                # errors for this can be
                # 'AbortError',
                # 'NotAllowedError',
                # 'NotFoundError',
                # 'NotReadableError',
                # 'OverconstrainedError',
                # 'SecurityError',
                # 'TypeError',
                Issue(
                    code='getusermedia_error',
                    type=Issue.TYPES_OF_ISSUES['warning'],
                    session=self.session,
                    participant=self.participant,
                    conference=self.conference,
                    data=self.data.get('error', {})
                ).save()

        elif self.type == 'onicecandidateerror':
            Issue(
                code='icecandidateerror',
                type=Issue.TYPES_OF_ISSUES['warning'],
                session=self.session,
                participant=self.participant,
                connection=self.connection,
                data=request_data.get('data', {})
            ).save()

        # this is not the most reliable way of telling if someone has left the page
        # the unload request might not be sent because some adblockers stop Beacon requests
        # so we need to also listen to this one to mark a session as ended
        # if the user canceled and didn't close the tab, then unload will also come at some point
        elif self.type == 'beforeunload':
            self.session.end_session(now)

        # participant left the page
        # or the user manually stopped the call
        elif self.type == 'unload' or self.type == 'endCall':
            # close all connections for this participant in this session
            for connection in self.participant.connections.filter(session=self.session):
                connection.end(now)
                connection.save()

            # mark the session as done
            self.session.end_session(now)

            self.conference.should_stop_call(now)

            # check if we have any issues
            Issue.check_end_session(session=self.session)

        elif self.type == 'addConnection':
            connection = Connection(
                session=self.session,
                conference=self.conference,
                participant=self.participant,
                peer_id=str(self.peer_id),
                start_time=now,
            )
            connection.save()

            self.connection = connection
            self.session.start_call(now)
            self.conference.start_call(now)

            connection_state = request_data.get('connectionState')
            if connection_state == 'connected':
                connection.state = connection_state
                connection.save()
            else:
                self.connection.add_negotiation(now, type='initial')

        elif self.type == 'removeConnection':
            self.connection.end(now)
            self.session.should_stop_call(now)
            self.conference.should_stop_call(now)

        elif self.type == 'addTrack':
            track_id = validate_string(request_data.get('trackId'))

            try:
                track = Track.get(connection=self.connection.id, track_id=track_id)
            except Track.DoesNotExist:
                track = Track(
                    connection=self.connection,
                    track_id=track_id,
                )
            self.track = track

        elif self.type == 'onnegotiationneeded':
            self.connection.add_negotiation(now, if_necessary=True)

        elif self.type == 'onsignalingstatechange':
            signaling_state = request_data.get('data', {}).get('signalingState')

            if signaling_state in ['have-local-offer', 'have-remote-offer']:
                self.connection.add_negotiation(now, if_necessary=True)
            elif signaling_state == 'stable':
                self.connection.update_last_negotiation('stable', now)

        elif self.type == 'onconnectionstatechange':
            # update connection state
            state = validate_string(request_data.get('data'))
            if state not in CONNECTION_STATE_ENUM:
                raise PMError(status=400, app_error=INVALID_PARAMETERS)

            self.connection.state = state

            # if self.connection.state == 'connecting':
            #     self.connection.add_negotiation(now, if_necessary=True)

            # if connection established successfully 
            if self.connection.state == 'connected':
                self.connection.update_last_negotiation('connected', now)

            # if it failed to establish
            if self.connection.state == 'failed':
                self.connection.update_last_negotiation('failed', now)
                Issue(
                    code='connection_failed',
                    type=Issue.TYPES_OF_ISSUES['error'],
                    session=self.session,
                    participant=self.participant,
                    connection=self.connection,
                    conference=self.conference,
                ).save()

            if self.connection.state == 'disconnected':
                Issue(
                    code='connection_disconnected',
                    type=Issue.TYPES_OF_ISSUES['warning'],
                    session=self.session,
                    participant=self.participant,
                    conference=self.conference,
                    connection=self.connection,
                ).save()

            # if connection was closed
            if self.connection.state == 'closed':
                self.connection.end(now)
                self.session.should_stop_call(now)
                self.conference.should_stop_call(now)

        elif self.type == 'oniceconnectionstatechange':
            if self.data == 'failed':
                Issue(
                    code='ice_failed',
                    type=Issue.TYPES_OF_ISSUES['error'],
                    session=self.session,
                    participant=self.participant,
                    conference=self.conference,
                    connection=self.connection,
                ).save()

        if self.connection:
            self.connection.save()

        self.session.save()
        self.conference.save()

        self.save()

    @staticmethod
    def get_type():
        return 'generic_event'

    def __str__(self):
        return str(self.id)
