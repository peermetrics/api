import datetime
import uuid

import validators
from django.db import transaction
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import JSONField

from .basemodel import BaseModel
from .organization import Organization

from ..logger import log


def validate_domain(domain):
    if not validators.domain(domain):
        raise ValidationError('Domain ({}) is not valid'.format(domain))


class App(BaseModel):
    """
    An abstraction of an app thar's being monitored by PeerMetrics.

    Attrs:
        cache_keys: combinations of fields used to compose the keys used to cache the object

    Fields:
        id: ID from db, UUID
        name: name for this app, set by user, string
        api_key: the key used by the app, string
        domain: the domain from which we should accept metrics, can be null, but it's recommended not to be, string
        organization: the organization that owns this app, an app will belong to one organization only, fk
        interval: how often should we collect info, seconds: 5, 10, 30, 60, int
        recording: whether the app is recording or not, bool
        durations_days: cache containing the durations of all the calls for the last data_retention days, dict
    """

    class Meta:
        db_table = 'app'

    cache_keys = (
        sorted(('id',)),
        sorted(('api_key',)),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(null=False, max_length=64, verbose_name="name for this app")
    api_key = models.CharField(unique=True, null=False, max_length=32)
    domain = models.CharField(max_length=256, null=True, blank=True, validators=[validate_domain])
    organization = models.ForeignKey(
        Organization,
        null=False,
        on_delete=models.CASCADE,
        verbose_name="the organization that owns this app", related_name='apps',
    )
    interval = models.IntegerField(default=settings.DEFAULT_INTERVAL)
    recording = models.BooleanField(default=True)
    durations_days = JSONField(null=True, blank=True, default=dict)
    created_at = models.DateTimeField(default=datetime.datetime.utcnow)
    is_active = models.BooleanField(default=True)

    @staticmethod
    def add_minutes(now, session, minutes_to_add):
        """
        Updates the minutes used by a user and an app when a session ends. Minutes are stored on the app in a cache for
        the last retention_days days.

        :param now: the time when the session ending event should have been received (it can be altered if the request
                    contains a delay)
        :param session: the session which has ended

        :param minutes_to_add: the time of used minutes
        """

        real_today = datetime.datetime.utcnow().date()
        today = now.date()

        with transaction.atomic():
            app = App.objects.select_for_update().get(id=session.conference.app_id, is_active=True)

            days = [real_today - datetime.timedelta(days=i) for i in range(settings.DEFAULT_BILLING_PERIOD_DAYS)]
            if today in days:
                new_cache = {str(day): app.durations_days.get(str(day), 0) for day in days}
                new_cache[str(today)] += minutes_to_add

            app.durations_days = new_cache

            app.save()

    def update_duration_days(self):
        """
        Method used to change the data stored in app.duration_days so that it does not contain data about days older
        than the time allowed by the owner's plan.
        """
        today = datetime.datetime.utcnow().date()

        days = [today - datetime.timedelta(days=i) for i in range(settings.DEFAULT_BILLING_PERIOD_DAYS)]
        new_cache = {str(day): self.durations_days.get(str(day), 0) for day in days}

        self.durations_days = new_cache

    @staticmethod
    def get_serialize_fix_duration_days_method():
        start_day = datetime.datetime.utcnow().date() - datetime.timedelta(days=settings.DEFAULT_BILLING_PERIOD_DAYS)
        end_day = datetime.datetime.utcnow().date()

        def serialize_fix_duration_days(serialized_app):
            if settings.DEV:
                return serialized_app

            if start_day > end_day:
                log.warning('app {app_id} had start_date bigger than end_date'.format(app_id=serialized_app['id']))
                return serialized_app

            day = start_day
            days = {}

            while day != end_day:
                days[str(day)] = serialized_app['durations_days'].get(str(day), 0)
                day += datetime.timedelta(days=1)
            serialized_app['durations_days'] = days

            return serialized_app
        return serialize_fix_duration_days

    def prepare(self):
        self.update_duration_days()
        self.save()

    @staticmethod
    def get_type():
        return 'app'

    def get_absolute_url(self):
        return ''.join([
            '/apps/',
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
