import datetime
import logging

from django.test import Client, TestCase
from django.conf import settings

from ..models.app import App
from ..models.conference import Conference
from ..models.organization import Organization
from ..models.participant import Participant
from ..models.subscription import Subscription
from ..models.user import User
from ..logger import log

log.setLevel(logging.ERROR)


class PMTestCase(TestCase):
    maxDiff = None

    def setUp(self):
        s = 'a9@a.com'
        self.user_password = 'password'
        self.user = User(
            username=s,
            email=s,
            billing={},
            notifications={},
            is_verified=True,
        )
        self.user.set_password(self.user_password)
        self.user.save()
        self.create_subscription(self.user)
        self.org = Organization(
            owner=self.user,
            name='test org'
        )
        self.org.save()
        self.org.members.add(self.user)

        self.app_recording = App(
            api_key='recb5da75a944da6a0fed919cc21d13c',
            organization=self.org,
            name='test app',
            recording=True,
        )
        self.app_recording.save()

        self.app_not_recording = App(
            api_key='nrec5da75a944da6a0fed919cc21d13c',
            organization=self.org,
            name='test app 2',
            recording=False,
        )
        self.app_not_recording.save()

        self.participant = Participant(
            participant_id='test',
            participant_name='test',
            app_id=self.app_recording.id
        )
        self.participant.save()

        self.other_participant = Participant(
            participant_id='test22',
            participant_name='test22',
            app_id=self.app_recording.id
        )
        self.other_participant.save()

        self.conference = Conference(
            conference_id='test',
            conference_name='test',
            app_id=self.app_recording.id
        )
        self.conference.save()
        self.participant.conferences.add(self.conference)
        self.other_participant.conferences.add(self.conference)
        self.client = Client()

    @staticmethod
    def create_subscription(user):
        subscription = Subscription(
            user=user,
            price=1,
            currency='EU',
            status='active',
            subscription_id='sub_id',
            customer_id='cus_id',
            current_period_end=datetime.datetime.utcnow(),
            current_period_start=datetime.datetime.utcnow(),
            plan_id=settings.FREE_PLAN_ID,
            current_billing_cycle=1,
            first_billing_date=datetime.datetime.utcnow(),
        )

        subscription.save()
