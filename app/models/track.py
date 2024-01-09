import datetime
import uuid

from django.contrib.postgres.fields import JSONField
from django.db import models

from .basemodel import BaseModel

AUDIO_VIDEO_ENUM = {
    'video': 'v',
    'audio': 'a',
}

DIRECTION_ENUM = {
    'inbound': 'i',
    'outbound': 'o',
}

class Track(BaseModel):
    """
    A Track is a WebRTC abstraction that represents a TODO.

    Attrs:
        cache_keys: combinations of fields used to compose the keys used to cache the object

    Fields:
        id: ID from db, UUID
        connection: the connection linked to the track, this can be null because tracks exist before connections fk
        track_id: the track id sent by the sdk, used to identify the track when saving stats events, string
        kind: the track kind (audio/video), string
        label: the label of the device that's producing the track, string
        track_info: info related to the connection, dict
            {
            TODO: add info about fields
            }
    """
    AUDIO_VIDEO_ENUM = AUDIO_VIDEO_ENUM

    DIRECTION_ENUM = DIRECTION_ENUM

    cache_keys = (
        sorted(('id',)),
    )

    def get_default_info(*args, **kwargs):
        return {
            'muted': None,
            'enabled': None,
            'capabilities': None,
            'constraints': [],
            'settings': None,
            'ended': False,
            'readyState': None,
            'contentHint': None,
        }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    session = models.ForeignKey('Session', on_delete=models.CASCADE, null=False, related_name='tracks')
    connection = models.ForeignKey('Connection', on_delete=models.CASCADE, null=True, blank=True, related_name='tracks')
    kind = models.CharField(
        max_length=1,
        choices=tuple([(AUDIO_VIDEO_ENUM[key], key) for key in AUDIO_VIDEO_ENUM.keys()]),
    )
    direction = models.CharField(
        max_length=1,
        choices=tuple([(DIRECTION_ENUM[key], key) for key in DIRECTION_ENUM.keys()])
    )
    track_id = models.CharField(max_length=40, db_index=True)
    label = models.CharField(null=True, blank=True, max_length=128)
    track_info = JSONField(null=True, blank=True, default=get_default_info)

    created_at = models.DateTimeField(default=datetime.datetime.utcnow)
    is_active = models.BooleanField(default=True)

    @staticmethod
    def create_tracks(track_list, session=None, direction=None, connection=None):
        # it's acceptable for track_list to be None, or be an empty list
        # that's why we need to do these checks
        if not isinstance(track_list, list) or len(track_list) == 0:
            return

        if direction not in DIRECTION_ENUM.keys():
            raise Exception('Invalid direction argument: {0}'.format(direction))

        if not session:
            raise Exception('Missing session argument')

        # loop through the list
        for track in track_list:
            new_track = Track(
                connection=connection,
                session=session,
                track_id=track.get('id')[:Track._meta.get_field('track_id').max_length],
                kind=AUDIO_VIDEO_ENUM.get(track.get('kind')),
                direction = DIRECTION_ENUM.get(direction),
                label=track.get('label')[:Track._meta.get_field('label').max_length],
            )

            new_track.track_info = {
                'muted': track.get('muted'),
                'enabled': track.get('enabled'),
                'capabilities': track.get('capabilities'),
                'constraints': [track.get('constraints')],
                'settings': track.get('settings'),
            }

            new_track.save()

    @staticmethod
    def get_type():
        return 'track'

    def __str__(self):
        return str(self.id)
