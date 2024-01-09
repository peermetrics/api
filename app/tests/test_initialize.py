import json

import jwt
from django.conf import settings

from ..errors import (APP_NOT_RECORDING, INVALID_API_KEY, INVALID_PARAMETERS,
                      MISSING_PARAMETERS, QUOTA_EXCEEDED, UNKNOWN_ERROR, DOMAIN_NOT_ALLOWED)
from ..models.app import App
from ..models.conference import Conference
from ..models.participant import Participant
from ..utils import JSONHttpResponse
from .classes import PMTestCase
from ..billing import Billing

class InitializeViewTestCase(PMTestCase):
    def test_post_no_data(self):
        response = self.client.post(
            path='/v1/initialize',
            data={},
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), UNKNOWN_ERROR)

    def test_post_missing_parameters(self):
        datas = [
            {
                'conferenceName': 'test',
                'userId': 'test',
                'userName': 'test',
                'apiKey': 'test',
            },
            {
                'conferenceId': 'test',
                'conferenceName': 'test',
                'userName': 'test',
                'apiKey': 'test',
            },
            {
                'conferenceId': 'test',
                'conferenceName': 'test',
                'userId': 'test',
                'userName': 'test',
            },
        ]

        for data in datas:
            response = self.client.post(
                path='/v1/initialize',
                data=data,
                content_type='application/json',
            )

            self.assertTrue(isinstance(response, JSONHttpResponse))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(json.loads(response.content), MISSING_PARAMETERS)

    def test_post_invalid_api_key(self):
        data = {
            'conferenceId': 'test',
            'conferenceName': 'test',
            'userId': 'test',
            'userName': 'test',
            'apiKey': 'invalid_key',
        }
        response = self.client.post(
            path='/v1/initialize',
            data=data,
            content_type='application/json',
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), INVALID_API_KEY)

    def test_post_invalid_api_key_no_app(self):
        data = {
            'conferenceId': 'test',
            'conferenceName': 'test',
            'userId': 'test',
            'userName': 'test',
            'apiKey': '74eb5da75a944da6a0fed919cc21d13c',
        }
        response = self.client.post(
            path='/v1/initialize',
            data=data,
            content_type='application/json',
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), INVALID_API_KEY)

    def test_post_app_not_recording(self):
        data = {
            'conferenceId': 'test',
            'conferenceName': 'test',
            'userId': 'test',
            'userName': 'test',
            'apiKey': self.app_not_recording.api_key,
        }
        response = self.client.post(
            path='/v1/initialize',
            data=data,
            content_type='application/json',
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), APP_NOT_RECORDING)

    def test_post_app_not_active(self):
        app_not_active = App(
            api_key='nact5da75a944da6a0fed919cc21d13c',
            organization=self.org,
            name='test app 21231234',
            recording=True,
            is_active=False
        )
        app_not_active.save()

        data = {
            'conferenceId': 'test',
            'conferenceName': 'test',
            'userId': 'test',
            'userName': 'test',
            'apiKey': app_not_active.api_key,
        }
        response = self.client.post(
            path='/v1/initialize',
            data=data,
            content_type='application/json',
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), INVALID_API_KEY)

    def test_post_invalid_params(self):
        inputs = [
            ('t' * 65, 'test', 'test', 'test'),
            ('test', 't' * 65, 'test', 'test'),
            ('test', 'test', 't' * 65, 'test'),
            ('test', 'test', 'test', 't' * 65),
        ]

        for inp in inputs:
            data = {
                'conferenceId': inp[0],
                'conferenceName': inp[1],
                'userId': inp[2],
                'userName': inp[3],
                'apiKey': self.app_recording.api_key,
            }
            response = self.client.post(
                path='/v1/initialize',
                data=data,
                content_type='application/json',
            )

            self.assertTrue(isinstance(response, JSONHttpResponse))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(json.loads(response.content), INVALID_PARAMETERS)

    def test_post_domain_not_allowed(self):
        app_invalid_domain = App(
            api_key='nact5da75a944da6a1234567cc21d13c',
            organization=self.org,
            name='test app 21231234',
            domain='different.domain',
            recording=True,
            is_active=True
        )
        app_invalid_domain.save()

        data = {
            'conferenceId': 'test',
            'conferenceName': 'test',
            'userId': 'test',
            'userName': 'test',
            'apiKey': app_invalid_domain.api_key,
        }
        response = self.client.post(
            path='/v1/initialize',
            data=data,
            content_type='application/json',
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(json.loads(response.content), DOMAIN_NOT_ALLOWED)

    def test_post_quota_exceeded(self):
        plan = Billing.get_user_plan(self.user)
        self.user.usage = plan['max_usage']
        self.user.save()

        api_key = self.app_recording.api_key
        participant_id = 'test'
        participant_name = 'test'
        conference_id = 'test'
        conference_name = 'test'

        data = {
            'conferenceId': conference_id,
            'conferenceName': conference_name,
            'userId': participant_id,
            'userName': participant_name,
            'apiKey': api_key,
        }

        response = self.client.post(
            path='/v1/initialize',
            data=data,
            content_type='application/json',
        )

        self.user.usage = 0
        self.user.save()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(json.loads(response.content), QUOTA_EXCEEDED)

    def test_post_200(self):
        api_key = self.app_recording.api_key
        participant_id = 'test'
        participant_name = 'test'
        conference_id = 'test'
        conference_name = 'test'

        data = {
            'conferenceId': conference_id,
            'conferenceName': conference_name,
            'userId': participant_id,
            'userName': participant_name,
            'apiKey': api_key,
        }

        response = self.client.post(
            path='/v1/initialize',
            data=data,
            content_type='application/json',
        )

        app = App.filter(api_key=api_key).first()

        participant = Participant.get(participant_id=participant_id, app=app)
        self.assertEqual(participant.participant_name, participant_name)

        conference = Conference.get(conference_id=conference_id, app=app)
        self.assertEqual(conference.conference_name, conference_name)

        participant.conferences.get(id=conference.id)

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        response_body = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response_body['getStatsInterval'], app.interval)

        token = response_body['token']

        token_payload = jwt.decode(
            token, settings.INIT_TOKEN_SECRET,
        )

        self.assertEqual(token_payload['p'], str(participant.id))
        self.assertEqual(token_payload['c'], str(conference.id))
        self.assertEqual(tuple(token_payload.keys()), ('p', 'c', 't'))
