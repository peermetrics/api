import datetime
import uuid

from django.contrib.postgres.fields import JSONField
from django.db import models

from .basemodel import BaseModel

from logging import warning

TYPE_OF_CONNECTIONS_ENUM = {
    'host': 'h',
    'srflx': 's',
    'prflx': 'p',
    'relay': 'r'
}

CONNECTION_STATE_ENUM = (
    'new',
    'connecting',
    'connected',
    'disconnected',
    'failed',
    'closed'
)

class Connection(BaseModel):
    """
    A connection is a WebRTC abstraction that represents a link between two participants.

    Attrs:
        cache_keys: combinations of fields used to compose the keys used to cache the object

    Fields:
        id: ID from db, UUID
        session: the session linked to the connection, fk
        participant: the participant linked to the connection, fk
        peer: the participant with whom the first participant is linked, fk
        connection_info: info related to the connection, dict
            {
                detected_tcp: bool to keep track if we detected at least once TCP data. used to save an issue
                detected_turn: bool. if we detected use of turn on this connection
                negotiations: list of negotiations, objects[]
                    start_time: string
                    status: state of negotiation, can have value connecting, connected, failed
                    end_time: string
                    duration: number

            }
    """
    TYPE_OF_CONNECTIONS_ENUM = TYPE_OF_CONNECTIONS_ENUM

    cache_keys = (
        sorted(('id',)),
    )

    def get_default_info(*args, **kwargs):
        return {
            'detected_tcp': False,
            'detected_turn': False,
            'negotiations': [],
        }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    session = models.ForeignKey('Session', on_delete=models.CASCADE, null=False, related_name='connections')
    conference = models.ForeignKey('Conference', on_delete=models.CASCADE, null=False, related_name='connections')
    participant = models.ForeignKey('Participant', on_delete=models.CASCADE, null=False, related_name='connections')
    peer = models.ForeignKey('Participant', on_delete=models.CASCADE, null=False, related_name='peer_connections')

    type = models.CharField(
        max_length=1, null=True, blank=True,
        choices=tuple([(TYPE_OF_CONNECTIONS_ENUM[key], key) for key in TYPE_OF_CONNECTIONS_ENUM.keys()]),
    )
    state = models.CharField(max_length=32, null=False, default='new')
    connection_info = JSONField(null=True, blank=True, default=get_default_info)
    start_time = models.DateTimeField(default=None, null=True, blank=True)
    end_time = models.DateTimeField(default=None, null=True, blank=True)
    duration = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(default=datetime.datetime.utcnow)
    is_active = models.BooleanField(default=True)

    def end(self, now):
        if not self.end_time:
            self.end_time = now
            self.duration = int((now - self.start_time).total_seconds())

            for negotiation in self.connection_info['negotiations']:
                if negotiation['end_time'] is None:
                    negotiation['end_time'] = str(now)
                    negotiation['status'] = 'failed'

    def add_negotiation(self, now, type='renegotiation', if_necessary=False):
        # if we only need to add it
        if if_necessary:
            negotiations = self.connection_info['negotiations']
            # if the last negotiation is already connecting
            # don't do anything
            try:
                if negotiations[-1]['status'] == 'connecting':
                    return
            except IndexError:
                # might throw a list out of index
                # we should add it
                pass

        self.connection_info['negotiations'].append({
            'start_time': str(now),
            'status': 'connecting',
            'type': type,
            'end_time': None,
            'duration': None,
        })

    def update_last_negotiation(self, status, now):
        try:
            last_negotiation = self.connection_info['negotiations'][-1]
        except IndexError:
            warning('Tried to get last negotiation but could not find any')

            self.add_negotiation(now)
            last_negotiation = self.connection_info['negotiations'][-1]

        last_negotiation['status'] = status
    
        if status in ['connected', 'stable']:
            start_time = datetime.datetime.fromisoformat(last_negotiation['start_time'])
            last_negotiation['end_time'] = str(now)
            last_negotiation['duration'] = int((now - start_time).total_seconds())

    @staticmethod
    def get_type():
        return 'connection'

    def __str__(self):
        return str(self.id)
