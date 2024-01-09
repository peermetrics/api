import datetime
import uuid

from django.db import models

from .basemodel import BaseModel


class Organization(BaseModel):
    """
    A group of users.

    Fields:
        id: ID from db, UUID
        name: name for this organization, set by the owner, string
        members: a list of users that have access to this organization; can read the stats, m2m
    """

    class Meta:
        db_table = 'organization'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(null=False, max_length=64)
    created_at = models.DateTimeField(default=datetime.datetime.utcnow)
    is_active = models.BooleanField(default=True)

    @staticmethod
    def get_type():
        return 'organization'

    def get_absolute_url(self):
        return ''.join([
            '/organization/',
            str(self.id),
        ])

    def get_name(self):
        return self.name

    def get_identifier(self):
        """
        Used to return the "ID" that the user provided for this model.
        N/A in this case
        """
        return ''

    def __str__(self):
        return str(self.id)
