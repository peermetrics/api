import datetime
import uuid

from django.contrib.postgres.fields import JSONField
from django.db import models

from .basemodel import BaseModel
from .app import App

import logging

class Session(BaseModel):
    """
    A session is a WebRTC abstraction that represents a participant's call session.

    Attrs:
        cache_keys: combinations of fields used to compose the keys used to cache the object

    Fields:
        id: ID from db, UUID
        conference: the conference linked to the session, fk
        participant: the participant linked to the session, fk

        constraints: the constraints of the session, part of the session data, dict
        devices: the devices of the session, part of the session data, dict
        platform: the platform of the session, part of the session data, dict
        metadata: the metadata of the session, dict
        geo_ip: geo_ip data of the session, dict
        app_version: the user's version of the app, string

        start_time: when the session started
        end_time: when the session ended, most likely user left the page

        call_start: when the user started to have an active connection

        session_info: info related to the session, dict
            {
                'warnings': ids of events with warnings related to the session,
                'gum_warnings': ids of getUserMedia events with warnings related to the session,
            }
    """
    cache_keys = (
        sorted(('id',)),
    )

    def get_default_info(*args, **kwargs):
        return {}

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    conference = models.ForeignKey('Conference', on_delete=models.CASCADE, null=False, related_name='sessions')
    participant = models.ForeignKey('Participant', on_delete=models.CASCADE, null=False, related_name='sessions')

    constraints = JSONField(null=True, blank=True, default=dict)
    devices = JSONField(null=True, blank=True, default=dict)
    platform = JSONField(null=True, blank=True, default=dict)
    metadata = JSONField(null=True, blank=True, default=dict)
    geo_ip = JSONField(null=True, blank=True, default=dict)
    app_version = models.CharField(null=True, blank=True, max_length=16)
    webrtc_sdk = models.CharField(null=True, blank=True, max_length=16)

    session_info = JSONField(null=True, blank=True, default=get_default_info)
    duration = models.PositiveIntegerField(default=0)
    end_time = models.DateTimeField(default=None, null=True, blank=True)

    call_start = models.DateTimeField(default=None, null=True, blank=True)

    created_at = models.DateTimeField(default=datetime.datetime.utcnow)
    is_active = models.BooleanField(default=True)

    @property
    def start_time(self):
        """
        Added just to have an equivalent of end_time
        """
        return self.created_at

    def start_call(self, now):
        if not self.call_start:
            self.call_start = now

    def check_if_ended(self):
        """
        Looks at all connections for this session and checks if there are all closed/ended
        """

        return all(connection.end_time is not None for connection in self.connections.all())

    def should_stop_call(self, now):
        """
        If we detect that all connections are terminated, mark the as done
        """

        if self.check_if_ended():
            # this can happen if the user had not active connections during a session
            if not self.call_start:
                # only log if this is actually the case
                if self.connections.count() != 0:
                    logging.debug('call_start is None at the end of the session')

                self.call_start = now

            # compute how many seconds the user had an active connection
            time_to_add = int((now - self.call_start).total_seconds())

            # add minutes to app
            App.add_minutes(now, self, time_to_add)

            # reset call start timestamp
            self.call_start = None

    def end_session(self, now):
        if not self.end_time:
            self.end_time = now
            self.duration = int((self.end_time - self.created_at).total_seconds())

        self.should_stop_call(now)

    @staticmethod
    def get_type():
        return 'session'

    def __str__(self):
        return str(self.id)
