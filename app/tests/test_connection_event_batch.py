import datetime
import json

import mock

from ..errors import INVALID_PARAMETERS, MISSING_PARAMETERS
from ..models.session import Session
from ..models.generic_event import GenericEvent
from ..utils import JSONHttpResponse, generate_session_token
from .classes import PMTestCase


class ConnectionEventBatchViewTestCase(PMTestCase):

    def test_post_missing_parameters(self):
        session = Session(
            participant=self.participant,
            conference=self.conference,
        )
        session.save()

        token = generate_session_token(session)

        data = {
            'token': token.decode('utf-8'),
            'data': [
                {
                    'eventName': 'ceva',
                    'data': '',
                    'timeDelta': 100,
                },
            ],
        }

        response = self.client.post(
            data=data,
            path='/v1/connection/batch',
            content_type='application/json',
            delta=2,
        )
        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), MISSING_PARAMETERS)

    def test_post_invalid_fields(self):
        session = Session(
            participant=self.participant,
            conference=self.conference,
        )
        session.save()

        token = generate_session_token(session)

        datas = [
            {
                'token': token.decode('utf-8'),
                'delta': 'string',
                'data': [
                    {
                        'eventName': 'ceva',
                        'data': '',
                        'timeDelta': 100,
                        'peerId': 'da'
                    },
                ],
            },
            {
                'token': token.decode('utf-8'),
                'delta': -3,
                'data': [
                    {
                        'eventName': 'ceva',
                        'data': '',
                        'timeDelta': 100,
                        'peerId': 'da'
                    },
                ],
            },
            {
                'token': token.decode('utf-8'),
                'delta': 3,
                'data': [
                    {
                        'eventName': 123,
                        'data': '',
                        'timeDelta': 100,
                        'peerId': 'da'
                    },
                ],
            },
            {
                'token': token.decode('utf-8'),
                'delta': 3,
                'data': [
                    {
                        'eventName': {},
                        'data': '',
                        'timeDelta': 100,
                        'peerId': 'da'
                    },
                ],
            },
            {
                'token': token.decode('utf-8'),
                'delta': 3,
                'data': [
                    {
                        'eventName': 'ceva',
                        'data': '',
                        'timeDelta': 100,
                        'peerId': 1
                    },
                ],
            },
            {
                'token': token.decode('utf-8'),
                'delta': 3,
                'data': [
                    {
                        'eventName': 'ceva',
                        'data': '',
                        'timeDelta': '100',
                        'peerId': 'da'
                    },
                ],
            },
            {
                'token': token.decode('utf-8'),
                'delta': 3,
                'data': [
                    {
                        'eventName': 'ceva',
                        'data': '',
                        'timeDelta': -23,
                        'peerId': 'da'
                    },
                ],
            },
        ]

        for data in datas:
            response = self.client.post(
                data=data,
                path='/v1/connection/batch',
                content_type='application/json',
                delta=2,
            )
            self.assertTrue(isinstance(response, JSONHttpResponse))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(json.loads(response.content), INVALID_PARAMETERS)

    def test_post_200(self):
        initial_process_event = GenericEvent.process_event
        process_event_mock = mock.Mock()
        GenericEvent.process_event = process_event_mock

        session = Session(
            participant=self.participant,
            conference=self.conference,
        )
        session.save()

        token = generate_session_token(session)

        data = {
            'token': token.decode('utf-8'),
            'data': [
                {
                    'eventName': 'ceva',
                    'data': '',
                    'timeDelta': 0,
                    'peerId': str(self.other_participant.id),
                },
                {
                    'eventName': 'ceva1',
                    'data': '',
                    'timeDelta': 100,
                    'peerId': str(self.other_participant.id),
                },
                {
                    'eventName': 'ceva2',
                    'data': '',
                    'timeDelta': 101,
                    'peerId': str(self.other_participant.id),
                },
            ],
        }

        response = self.client.post(
            data=data,
            path='/v1/connection/batch',
            content_type='application/json',
            delta=2,
        )
        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), '')

        first = process_event_mock.call_args_list[0].kwargs['now']
        self.assertEqual(process_event_mock.call_args_list[1].kwargs['now'], first - datetime.timedelta(milliseconds=data['data'][1]['timeDelta']))
        self.assertEqual(process_event_mock.call_args_list[2].kwargs['now'], first - datetime.timedelta(milliseconds=data['data'][2]['timeDelta']))

        GenericEvent.process_event = initial_process_event
