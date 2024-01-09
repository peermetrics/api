import datetime
import uuid

from django.db import models

from .app import App
from .basemodel import BaseModel
from .conference import Conference


class Participant(BaseModel):
    """
    A participant is an endpoint (eg browser) for which we gathered stats at one point.
    A participant is made unique by the combination: app_id:user_id.
    The user_id is set by the client's SDK.

    Attrs:
        cache_keys: combinations of fields used to compose the keys used to cache the object

    Fields:
        id: ID from db, UUID
        participant_id: participant id set by user, string
        participant_name: participant name set by user, string
        is_sfu: if this participant is a SFU server, boolean
        app: the app which created the participant, fk
        conferences: the list of conferences this participant took part of, m2m
    """

    class Meta:
        db_table = 'participant'
        unique_together = (('participant_id', 'app'),)

    cache_keys = (
        sorted(('id',)),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    participant_id = models.CharField(null=False, max_length=64, db_index=True)
    participant_name = models.CharField(null=True, max_length=64, blank=True)
    is_sfu = models.BooleanField(default=False)
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name='participants')
    conferences = models.ManyToManyField(Conference, blank=True, default=None, related_name='participants')
    created_at = models.DateTimeField(default=datetime.datetime.utcnow)
    is_active = models.BooleanField(default=True)

    @staticmethod
    def get_type():
        return 'participant'

    def get_absolute_url(self):
        return ''.join([
            '/participant/',
            str(self.id),
        ])

    def get_name(self):
        return self.participant_name

    def get_identifier(self):
        """Used to return the "ID" that the user provided for this model"""

        return self.participant_id

    def __str__(self):
        return str(self.id)
