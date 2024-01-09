import datetime
import json
import time
import uuid

import jwt
from django.conf import settings

from ..errors import (APP_NOT_FOUND, CONFERENCE_NOT_FOUND, INVALID_META, INVALID_PARAMETERS,
                      MISSING_PARAMETERS, PARTICIPANT_NOT_FOUND, UNKNOWN_ERROR)
from ..models.app import App
from ..models.conference import Conference
from ..models.participant import Participant
from ..models.session import Session
from ..models.user import User
from ..utils import JSONHttpResponse, serialize, generate_token, generate_session_token
from .classes import PMTestCase
from ..billing import Billing


class SessionViewTestCase(PMTestCase):
    def test_get_missing_parameters(self):
        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        response = self.client.get('/v1/sessions')

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), MISSING_PARAMETERS)

        self.client.logout()

    def test_get_invalid_ids_or_not_found_or_not_active(self):
        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )
        self.create_subscription(user)

        self.org.members.add(user)
        self.org.save()

        app_not_active = App(
            api_key='nact5weg5a944da6a0fed919cc21d13c',
            organization=self.org,
            name='test app 2234234234',
            domain='cv.cv',
            recording=True,
            is_active=False,
        )
        app_not_active.save()

        participant_not_active = Participant(
            participant_id='test 345',
            participant_name='test',
            app_id=app_not_active.id,
            is_active=False,
        )
        participant_not_active.save()

        conference_not_active = Conference(
            conference_id='test 345',
            conference_name='test',
            app_id=app_not_active.id,
            is_active=False,
        )
        conference_not_active.save()

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        inputs = [
            ('1', '1', '', CONFERENCE_NOT_FOUND),
            ('1asdasd', '', '', CONFERENCE_NOT_FOUND),
            ('', '1', '1', PARTICIPANT_NOT_FOUND),
            ('', 'dasdasd1', '1', PARTICIPANT_NOT_FOUND),
            ('', '', '1', APP_NOT_FOUND),
            ('', '', 'dasdasd1', APP_NOT_FOUND),
            (str(uuid.uuid4()), '1', '1', CONFERENCE_NOT_FOUND),
            ('', str(uuid.uuid4()), '1', PARTICIPANT_NOT_FOUND),
            ('', '', str(uuid.uuid4()), APP_NOT_FOUND),
            (str(self.conference.id), str(uuid.uuid4()), '1', PARTICIPANT_NOT_FOUND),
            (str(self.conference.id), participant_not_active.id, '1', PARTICIPANT_NOT_FOUND),
            (str(self.conference.id), str(self.participant.id), str(uuid.uuid4()), APP_NOT_FOUND),
            (str(self.conference.id), str(self.participant.id), app_not_active.id, APP_NOT_FOUND),
            (str(uuid.uuid4()), str(self.participant.id), '1', CONFERENCE_NOT_FOUND),
            (conference_not_active.id, str(self.participant.id), '1', CONFERENCE_NOT_FOUND),
            (str(uuid.uuid4()), str(uuid.uuid4()), str(self.app_recording.id), CONFERENCE_NOT_FOUND),
        ]

        for inp in inputs:

            data = {
                'conferenceId': inp[0],
                'participantId': inp[1],
                'appId': inp[2],
            }
            expected_error = inp[3]

            response = self.client.get(
                path='/v1/sessions',
                data=data,
            )

            self.assertTrue(isinstance(response, JSONHttpResponse))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(json.loads(response.content), expected_error)

        self.client.logout()

    def test_get_no_user_permission(self):

        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )
        self.create_subscription(user)

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        Session(
            conference=self.conference,
            participant=self.participant,
            metadata='test3',
        ).save()

        inputs = [
            (self.conference.id, '', '', CONFERENCE_NOT_FOUND),
            ('', self.participant.id, '', PARTICIPANT_NOT_FOUND),
            ('', '', self.app_recording.id, APP_NOT_FOUND),
        ]

        for inp in inputs:

            data = {
                'conferenceId': inp[0],
                'participantId': inp[1],
                'appId': inp[2],
            }
            expected_error = inp[3]

            response = self.client.get(
                path='/v1/sessions',
                data=data,
            )

            self.assertTrue(isinstance(response, JSONHttpResponse))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(json.loads(response.content), expected_error)

        self.client.logout()

    def test_get_200(self):
        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        self.org.members.add(self.user)
        self.org.save()

        app = App(
            api_key='aact5weg5a944da6a0fed919cc21d13c',
            organization=self.org,
            name='test app 23r2r23r23r',
            domain='cv.cv',
            recording=True,
        )
        app.save()

        app_conference = Conference(
            conference_id='test 345',
            conference_name='test',
            app=app,
            is_active=True,
        )
        app_conference.save()

        other_participant = Participant(
            participant_id='test2',
            participant_name='test2',
            app_id=self.app_recording.id
        )
        other_participant.save()

        other_conference = Conference(
            conference_id='test2',
            conference_name='test2',
            app_id=self.app_recording.id
        )
        other_conference.save()

        Session(
            conference=self.conference,
            participant=other_participant,
            metadata='test1',
        ).save()
        Session(
            conference=other_conference,
            participant=self.participant,
            metadata='test2',
        ).save()
        Session(
            conference=self.conference,
            participant=self.participant,
            metadata='test3',
        ).save()

        Session(
            conference=app_conference,
            participant=self.participant,
            metadata='test2',
        ).save()
        Session(
            conference=app_conference,
            participant=self.participant,
            metadata='test3',
        ).save()

        inputs = [
            {
                'data': {
                    'conferenceId': str(self.conference.id),
                },
                'expected': serialize(
                    objs=Session.filter(conference=self.conference),
                    blacklist=('is_active', 'constraints', ),
                ),
            },
            {
                'data': {
                    'participantId': str(self.participant.id),
                },
                'expected': serialize(
                    objs=Session.filter(participant=self.participant),
                    blacklist=('is_active', 'constraints', ),
                ),
            },
            {
                'data': {
                    'conferenceId': str(self.conference.id),
                    'participantId': str(self.participant.id),
                },
                'expected': serialize(
                    objs=Session.filter(
                        conference=self.conference,
                        participant=self.participant,
                    ),
                    blacklist=('is_active', 'constraints', ),
                ),
            },
            {
                'data': {
                    'appId': str(app.id),
                },
                'expected': serialize(
                    objs=Session.filter(
                        conference__id__in=Conference.filter(
                            app=app,
                        ).values_list('id', flat=True),
                    ),
                    blacklist=('is_active', 'constraints',),
                ),
            },
        ]

        for inp in inputs:

            response = self.client.get(
                path='/v1/sessions',
                data=inp['data'],
            )

            self.assertTrue(isinstance(response, JSONHttpResponse))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.content.decode('utf-8')), inp['expected'])

        self.client.logout()

    def test_get_200_no_session_max_days(self):
        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        max_days = Billing.get_data_retention_days(self.user)

        Session(
            conference=self.conference,
            participant=self.participant,
            metadata='test1',
            created_at=datetime.datetime.utcnow() - datetime.timedelta(days=max_days + 1),
        ).save()

        data = {
            'conferenceId': str(self.conference.id),
        }
        expected = {
            'data': [],
        }

        response = self.client.get(
            path='/v1/sessions',
            data=data,
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)

        self.client.logout()

    def test_post_invalid_data(self):
        payload = {
            'p': str(self.participant.id),
            'c': str(self.conference.id),
            't': time.time(),
        }

        token = generate_token(
            payload=payload,
            secret=settings.INIT_TOKEN_SECRET,
        )

        response = self.client.post(
            path='/v1/sessions',
            data={
                'token': token.decode('utf-8'),
            },
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), UNKNOWN_ERROR)

    def test_post_invalid_parameters(self):

        payload = {
            'p': str(self.participant.id),
            'c': str(self.conference.id),
            't': time.time(),
        }

        token = generate_token(
            payload=payload,
            secret=settings.INIT_TOKEN_SECRET,
        )

        meta = {'meta': 'meta'}
        constraints = ('constraints', )
        devices = {'devices': 'dict'}
        platform = ['platform', 'da']

        invalid_app_versions = [
            17 * 'c',
            17,
            {1: 5},
        ]

        for invalid_app_version in invalid_app_versions:
            response = self.client.post(
                path='/v1/sessions',
                data={
                    'token': token.decode('utf-8'),
                    'meta': meta,
                    'constraints': constraints,
                    'devices': devices,
                    'platform': platform,
                    'appVersion': invalid_app_version,
                },
                content_type='application/json',
            )

            self.assertTrue(isinstance(response, JSONHttpResponse))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(json.loads(response.content), INVALID_PARAMETERS)

    def test_post_invalid_meta(self):

        payload = {
            'p': str(self.participant.id),
            'c': str(self.conference.id),
            't': time.time(),
        }

        token = generate_token(
            payload=payload,
            secret=settings.INIT_TOKEN_SECRET,
        )

        meta = 'meta'
        constraints = ('constraints', )
        devices = {'devices': 'dict'}
        platform = ['platform', 'da']

        response = self.client.post(
            path='/v1/sessions',
            data={
                'token': token.decode('utf-8'),
                'meta': meta,
                'constraints': constraints,
                'devices': devices,
                'platform': platform,
            },
            content_type='application/json',
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), INVALID_META)

    def test_post_200(self):

        payload = {
            'p': str(self.participant.id),
            'c': str(self.conference.id),
            't': time.time(),
        }

        token = generate_token(
            payload=payload,
            secret=settings.INIT_TOKEN_SECRET,
        )

        meta = {'meta': 'meta'}
        constraints = ('constraints', )
        devices = {'devices': 'dict'}
        platform = ['platform', 'da']

        response = self.client.post(
            path='/v1/sessions',
            data={
                'token': token.decode('utf-8'),
                'meta': meta,
                'constraints': constraints,
                'devices': devices,
                'platform': platform,
            },
            content_type='application/json',
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        token = json.loads(response.content.decode('utf-8'))['token']

        token_payload = jwt.decode(token, settings.SESSION_TOKEN_SECRET)
        self.assertEqual(tuple(token_payload.keys()), ('s', 't'))

        session = Session.get(pk=token_payload['s'])

        self.assertEqual(session.conference, self.conference)
        self.assertEqual(session.participant, self.participant)

        self.assertEqual(session.metadata, meta)
        self.assertEqual(session.constraints, list(constraints))
        self.assertEqual(session.devices, devices)
        self.assertEqual(session.platform, platform)

    def test_put_invalid_data(self):
        session = Session(
            participant=self.participant,
            conference=self.conference,
        )
        session.save()

        token = generate_session_token(session)

        response = self.client.put(
            path='/v1/sessions',
            data={
                'token': token.decode('utf-8'),
            },
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), UNKNOWN_ERROR)

    def test_put_no_parameters(self):
        session = Session(
            participant=self.participant,
            conference=self.conference,
        )
        session.save()

        token = generate_session_token(session)

        response = self.client.put(
            path='/v1/sessions',
            data={
                'token': token.decode('utf-8'),
            },
            content_type='application/json',
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        response_body = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response_body, serialize([session], return_single_object=True))

    def test_put_no_change_parameters(self):
        session = Session(
            participant=self.participant,
            conference=self.conference,
            constraints='test',
            devices='test',
            platform='test',
        )
        session.save()

        token = generate_session_token(session)

        response = self.client.put(
            path='/v1/sessions',
            data={
                'token': token.decode('utf-8'),
                'devices': session.devices,
                'constraints': session.constraints,
                'platform': session.platform,
                'metadata': 'changed',
            },
            content_type='application/json',
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        response_body = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response_body, serialize([session], return_single_object=True))

    def test_put_200(self):
        session = Session(
            participant=self.participant,
            conference=self.conference,
            constraints='test',
            devices='test',
            platform='test',
        )
        session.save()

        token = generate_session_token(session)

        response = self.client.put(
            path='/v1/sessions',
            data={
                'token': token.decode('utf-8'),
                'devices': 'test2',
                'constraints': 'test23',
                'platform': 'test24',
            },
            content_type='application/json',
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        response_body = json.loads(response.content.decode('utf-8'))

        attr_white_list = [
            'constraints',
            'devices',
            'platform',
        ]

        updated_session = Session.get(pk=session.pk)

        for key in attr_white_list:
            self.assertNotEqual(response_body['data'][key], str(getattr(session, key)))
            assert (
                str(getattr(session, key)) != str(getattr(updated_session, key))
                and str(getattr(session, key)) != getattr(updated_session, key)
            )

        self.assertEqual(response_body, serialize([updated_session], return_single_object=True))
