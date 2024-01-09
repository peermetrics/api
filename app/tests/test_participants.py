import datetime
import json
import urllib
import uuid

from ..errors import (PARTICIPANT_NOT_FOUND, INVALID_PARAMETERS,
                      MISSING_PARAMETERS, METHOD_NOT_ALLOWED)
from ..models.user import User
from ..models.participant import Participant
from ..models.subscription import Subscription
from ..utils import JSONHttpResponse, serialize
from .classes import PMTestCase
from ..billing import Billing


class ParticipantViewTestCase(PMTestCase):

    def test_get_no_conference(self):
        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        response = self.client.get(
            path='/v1/participants/{}'.format(str(uuid.uuid4())),
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), PARTICIPANT_NOT_FOUND)

    def test_get_user_not_org(self):
        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        response = self.client.get(
            path='/v1/participants/{}'.format(str(self.participant.id)),
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), PARTICIPANT_NOT_FOUND)

    def test_get_200(self):
        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        response = self.client.get(
            path='/v1/participants/{}'.format(str(self.participant.id)),
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            json.loads(response.content.decode('utf-8')),
            serialize(
                [self.participant],
                return_single_object=True,
            ),
        )

    def test_filter_missing_params(self):
        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        response = self.client.get(
            path='/v1/participants',
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), MISSING_PARAMETERS)

    def test_filter_400_invalid_params(self):
        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        filters_list = [
            (
                '1',
                str(datetime.datetime.utcnow() - datetime.timedelta(days=1)),
                str(datetime.datetime.utcnow() - datetime.timedelta(days=1)),
            ),
        ]

        for filters in filters_list:
            response = self.client.get(
                path='/v1/participants?{}'.format(urllib.parse.urlencode({
                    'appId': filters[0],
                    'created_at__gt': filters[1],
                    'created_at__lt': filters[2],
                })),
            )
            self.assertTrue(isinstance(response, JSONHttpResponse))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(json.loads(response.content), INVALID_PARAMETERS)

        self.client.logout()

    def test_filter_200_user_not_in_org(self):
        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )
        self.create_subscription(user)

        self.assertTrue(self.client.login(username=user.username, password=user_password))
        urllib.parse.urlencode({
            'appId': str(self.participant.app.id),
            'created_at_gt': str(datetime.datetime.utcnow() - datetime.timedelta(days=1)),
            'created_at__lt': str(datetime.datetime.utcnow()),
        })
        response = self.client.get(
            path='/v1/participants?{}'.format(urllib.parse.urlencode({
                'appId': str(self.participant.app.id),
                'created_at_gt': str(datetime.datetime.utcnow() - datetime.timedelta(days=1)),
                'created_at__lt': str(datetime.datetime.utcnow()),
            })),
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content.decode('utf-8')), {'data': []})

    def test_filter_200(self):
        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        response = self.client.get(
            path='/v1/participants?{}'.format(urllib.parse.urlencode({
                'appId': str(self.participant.app.id),
                'created_at_gt': str(datetime.datetime.utcnow() - datetime.timedelta(days=1)),
                'created_at__lt': str(datetime.datetime.utcnow()),
            })),
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        self.participant.refresh_from_db()
        self.other_participant.refresh_from_db()

        self.assertEqual(
            json.loads(response.content.decode('utf-8')),
            serialize(
                [self.participant, self.other_participant],
            ),
        )

    def test_filter_200_no_particiants(self):
        max_days = Billing.get_data_retention_days(self.user)

        Participant(
            participant_id='test 2',
            participant_name='test 2',
            app_id=self.app_recording.id,
            created_at=datetime.datetime.utcnow() - datetime.timedelta(days=max_days + 4),
        ).save()

        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        filters_list = [
            (
                str(self.participant.app.id),
                str(datetime.datetime.utcnow() - datetime.timedelta(days=1)),
                str(datetime.datetime.utcnow() - datetime.timedelta(days=1)),
            ),
            (
                str(uuid.uuid4()),
                str(datetime.datetime.utcnow() - datetime.timedelta(days=1)),
                str(datetime.datetime.utcnow()),
            ),
            (
                str(self.participant.app.id),
                str(datetime.datetime.utcnow() + datetime.timedelta(days=1)),
                str(datetime.datetime.utcnow()),
            ),
        ]

        for filters in filters_list:
            response = self.client.get(
                path='/v1/participants?{}'.format(urllib.parse.urlencode({
                    'appId': filters[0],
                    'created_at_gt': filters[1],
                    'created_at_lt': filters[2],
                })),
            )

            self.assertTrue(isinstance(response, JSONHttpResponse))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.content.decode('utf-8')), {'data': []})

        self.client.logout()

    def test_delete_405(self):
        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        response = self.client.delete(
            path='/v1/participants/{}'.format(str(uuid.uuid4())),
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 405)
        self.assertEqual(json.loads(response.content), METHOD_NOT_ALLOWED)
