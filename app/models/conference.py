import datetime
import uuid

from django.db import models
from django.contrib.postgres.fields import JSONField

from .app import App
from .basemodel import BaseModel

from ..utils import build_conference_summary

import logging

class Conference(BaseModel):
    """
    A conference is a WebRTC call where more than 1 participant is present. It gets created when a participant
    connects for the first time.

    Attrs:
        cache_keys: combinations of fields used to compose the keys used to cache the object

    Fields:
        id: ID from db, UUID
        conference_id: conference id set by user, string
        conference_name: conference name set by user, string
        start_time: timestamp of the first connected event
        call_start: timestamp when the current "call" has started (most recent connection)
        end_time: timestamp when the last connection closed
        ongoing: boolean showing if the call is active
        duration: the total time connections were active
        conference_info: conference info, dict
             {
                 'had_connection_error':
             }
        app: the app which created the conference, fk
    """

    class Meta:
        db_table = 'conference'

    cache_keys = (
        sorted(('id',)),
    )

    def get_default_info(*args, **kwargs):
        return {}

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    conference_id = models.CharField(null=False, max_length=64, db_index=True)
    conference_name = models.CharField(null=True, blank=True, max_length=64)
    conference_info = JSONField(null=True, blank=True, default=get_default_info)

    start_time = models.DateTimeField(default=None, null=True, blank=True)
    call_start = models.DateTimeField(default=None, null=True, blank=True)
    end_time = models.DateTimeField(default=None, null=True, blank=True)
    ongoing = models.BooleanField(default=False)
    duration = models.PositiveIntegerField(default=0)

    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name='conferences')

    created_at = models.DateTimeField(default=datetime.datetime.utcnow)
    is_active = models.BooleanField(default=True)

    def start_call(self, now):
        self.ongoing = True

        # this is only instanted once
        if not self.start_time:
            self.start_time = now

        # this gets instanted every time
        # we have an active connection in this conference
        if not self.call_start:
            self.call_start = now

    def check_if_ended(self):
        return all(connection.end_time is not None for connection in self.connections.all())

    def should_stop_call(self, now):
        if self.check_if_ended():
            if not self.call_start:
                if self.connections.count() != 0:
                    logging.warning('call_start is None at the end of the session')

                self.call_start = now

            self.duration += int((now - self.call_start).total_seconds())
            self.call_start = None
            self.end_time = now
            self.ongoing = False

            build_conference_summary(self)

    @staticmethod
    def get_type():
        return 'conference'

    def get_absolute_url(self):
        return ''.join([
            '/conference/',
            str(self.id),
        ])

    def get_name(self):
        return self.conference_name

    def get_identifier(self):
        """Used to return the "ID" that the user provided for this model"""

        return self.conference_id

    def __str__(self):
        return str(self.id)
