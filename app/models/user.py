import datetime
import time
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import JSONField
from django.db import models

from .basemodel import BaseModel
from ..logger import log


class User(AbstractUser, BaseModel):
    """
    User model.

    Fields:
        id: ID from db, UUID
        organization: the organization this user belongs to, fk
        last_active: the last time the user was active, date
        notifications: notifications, dict
        is_verified: True if the user verified the provided email, bool
        days_filter: default number of days to look back when querying events, int
    """

    class Meta:
        app_label = 'app'
        db_table = 'users'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    organization = models.ForeignKey(
        'Organization',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text='The organization this user belongs to'
    )
    last_active = models.DateField(default=datetime.datetime.utcnow, null=True, blank=True)
    notifications = JSONField(null=True, blank=True, default=dict)
    is_verified = models.BooleanField(default=False)

    days_filter = models.PositiveIntegerField(null=False, blank=True, default=30)
    usage = models.PositiveIntegerField(null=False, blank=True, default=0)

    created_at = models.DateTimeField(default=datetime.datetime.utcnow)

    def update_last_active(self):
        """
        Updates the last_active field if the user used the website during a new day.
        """
        if self.last_active != datetime.datetime.utcnow().date():
            self.last_active = datetime.datetime.utcnow().date()
            self.save()

    @staticmethod
    def get_type():
        return 'user'

    def __str__(self):
        return self.username
