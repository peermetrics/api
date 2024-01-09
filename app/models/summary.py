import datetime
import uuid

from django.db import models
from django.contrib.postgres.fields import JSONField

from .basemodel import BaseModel
from .conference import Conference

import logging

SUMMARY_STATUS_ENUM = {
    'ongoing': 'o',
    'done': 'd',
    'error': 'e'
}

CURRENT_SUMMARY_VERSION = 1

class Summary(BaseModel):
    """
    Used to create a summary for a conference. All the details are saved as json in data
    """

    class Meta:
        db_table = 'summary'

    cache_keys = (
        sorted(('id',)),
    )

    def get_default_data(): 
        return {}

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    status = models.CharField(
        max_length=1,
        choices=tuple([(SUMMARY_STATUS_ENUM[key], key) for key in SUMMARY_STATUS_ENUM.keys()]),
        default=SUMMARY_STATUS_ENUM['ongoing']
    )
    conference = models.OneToOneField(Conference, null=False, on_delete=models.CASCADE, related_name='summary')

    version = models.PositiveIntegerField(default=CURRENT_SUMMARY_VERSION)

    end_time = models.DateTimeField(default=None, null=True, blank=True)

    data = JSONField(null=True, blank=True, default=get_default_data)

    created_at = models.DateTimeField(default=datetime.datetime.utcnow)
    is_active = models.BooleanField(default=True)

    @staticmethod
    def get_type():
        return 'summary'

    def __str__(self):
        return str(self.id)
