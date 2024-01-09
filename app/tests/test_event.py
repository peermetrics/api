import datetime
import json
import uuid

import mock
from django.conf import settings

from ..errors import (CONFERENCE_NOT_FOUND, INVALID_PARAMETERS,
                      MISSING_PARAMETERS, PARTICIPANT_NOT_FOUND)
from ..models.app import App
from ..models.conference import Conference
from ..models.generic_event import GenericEvent
from ..models.participant import Participant
from ..models.session import Session
from ..models.user import User
from ..utils import JSONHttpResponse, generate_session_token, serialize
from .classes import PMTestCase


class EventViewTestCase(PMTestCase):
    get_urls = {
        '/v1/events/get-user-media': 'getUserMedia',
        '/v1/events/browser': 'browser',
        '/v1/connection': 'connection',
        '/v1/stats': 'stats',
    }

    post_urls = [
        '/v1/events/get-user-media',
        '/v1/events/browser',
        '/v1/connection',
    ]

    def post_all(self, data, **kwargs):
        return [self.client.post(path=url, data=data, **kwargs) for url in self.post_urls]

    def test_post_missing_arguments(self):
        session = Session(
            participant=self.participant,
            conference=self.conference,
        )
        session.save()

        token = generate_session_token(session)

        responses = self.post_all(
            data={'token': token.decode('utf-8')},
            content_type='application/json',
        )

        for response in responses:
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

        responses = []
        responses.extend(self.post_all(
            data={
                'token': token.decode('utf-8'),
                'eventName': 'typetypetypetypetypetypetypetype1',
                'peerId': str(self.other_participant.id),
            },
            content_type='application/json',
        ))

        responses.extend(self.post_all(
            data={
                'token': token.decode('utf-8'),
                'eventName': {'1': 23, '12': 23, '12123': 23, '11232': 23, '1342': 23, '1453452': 23},
                'peerId': str(self.other_participant.id),
            },
            content_type='application/json',
        ))

        for response in responses:
            self.assertTrue(isinstance(response, JSONHttpResponse))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(json.loads(response.content), INVALID_PARAMETERS)

    def test_post_200(self):
        session = Session(
            participant=self.participant,
            conference=self.conference,
        )
        session.save()

        token = generate_session_token(session)

        responses = self.post_all(
            data={
                'token': token.decode('utf-8'),
                'eventName': 'ceva',
                'peerId': str(self.other_participant.id),
            },
            content_type='application/json',
        )

        for response in responses:
            self.assertTrue(isinstance(response, JSONHttpResponse))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.content), '')

        events_no = GenericEvent.objects.filter(
            session=session,
        ).count()

        self.assertEqual(events_no, len(responses))

    def test_post_invalid_delta(self):
        session = Session(
            participant=self.participant,
            conference=self.conference,
        )
        session.save()

        token = generate_session_token(session)

        responses = self.post_all(
            data={
                'token': token.decode('utf-8'),
                'eventName': 'ceva',
                'peerId': 'da',
                'delta': -100,
            },
            content_type='application/json',
        )

        for response in responses:
            self.assertTrue(isinstance(response, JSONHttpResponse))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(json.loads(response.content), INVALID_PARAMETERS)

    def test_post_200_delta(self):
        initial_process_event = GenericEvent.process_event
        process_event_mock = mock.Mock()
        GenericEvent.process_event = process_event_mock

        session = Session(
            participant=self.participant,
            conference=self.conference,
        )
        session.save()

        token = generate_session_token(session)

        self.client.post(
            data={
                'token': token.decode('utf-8'),
                'eventName': 'ceva',
                'peerId': str(self.other_participant.id),
                'delta': 10000000000000,
            },
            path='/v1/connection',
            content_type='application/json',
        )

        self.assertEqual(process_event_mock.call_count, 1)
        self.assertTrue(process_event_mock.call_args[1]['now'] < datetime.datetime.utcnow() - datetime.timedelta(days=2))

        GenericEvent.process_event = initial_process_event

    def test_post_200_warnings(self):
        other_conference = Conference(
            conference_id='test2',
            conference_name='test2',
            app_id=self.app_recording.id
        )
        other_conference.save()

        session = Session(
            participant=self.participant,
            conference=other_conference,
        )
        session.save()

        token = generate_session_token(session)

        datas = [
            {
                'token': token.decode('utf-8'),
                'eventName': 'icecandidateerror',
                'data': 500,
            },
            {
                'token': token.decode('utf-8'),
                'eventName': 'onconnectionstatechange',
                'data': 'disconnected',
            },
            {
                'token': token.decode('utf-8'),
                'eventName': 'oniceconnectionstatechange',
                'data': 'failed',
            },
        ]

        responses = [
            self.client.post(data=data, path='/v1/events/browser', content_type='application/json') for data in datas
        ]

        for response in responses:
            self.assertTrue(isinstance(response, JSONHttpResponse))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.content), '')

        self.assertEqual(session.session_info, {'warnings': [], 'gum_warnings': [], 'connections': [], 'start_call': None, 'call_count': 0})
        session.refresh_from_db()

        events = GenericEvent.objects.filter(
            session=session,
        )

        self.assertEqual(sorted(list(session.session_info.keys())), sorted(['warnings', 'call_count', 'start_call', 'connections', 'gum_warnings']))
        self.assertEqual(session.session_info['call_count'], 0)
        self.assertEqual(session.session_info['start_call'], None)
        self.assertEqual(session.session_info['gum_warnings'], [])
        self.assertEqual(session.session_info['connections'], [])

        self.assertEqual(len(session.session_info['warnings']), 3)
        for event in events:
            self.assertTrue({str(event.id): event.type} in session.session_info['warnings'])

        self.assertEqual(len(events), len(responses))

    def test_post_200_gum_warnings(self):

        other_conference = Conference(
            conference_id='test2',
            conference_name='test2',
            app_id=self.app_recording.id
        )
        other_conference.save()

        session = Session(
            participant=self.participant,
            conference=other_conference,
        )
        session.save()

        token = generate_session_token(session)

        datas = [
            {
                'token': token.decode('utf-8'),
                'eventName': 'getUserMedia',
                'data': {
                    'error': {
                        'name': 'AbortError',
                    },
                },
            },
            {
                'token': token.decode('utf-8'),
                'eventName': 'getUserMedia',
                'data': {
                    'error': {
                        'name': 'NotFoundError',
                    },
                },
            },
            {
                'token': token.decode('utf-8'),
                'eventName': 'getUserMedia',
                'data': {
                    'error': {
                        'name': 'SecurityError',
                    },
                },
            },
        ]

        responses = [
            self.client.post(
                data=data, path='/v1/events/get-user-media', content_type='application/json'
            ) for data in datas
        ]

        self.assertEqual(session.session_info, {'warnings': [], 'gum_warnings': [], 'connections': [], 'start_call': None, 'call_count': 0})
        session.refresh_from_db()

        for response in responses:
            self.assertTrue(isinstance(response, JSONHttpResponse))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.content), '')

        self.assertEqual(sorted(list(session.session_info.keys())), sorted(['warnings', 'call_count', 'start_call', 'connections', 'gum_warnings']))
        self.assertEqual(session.session_info['call_count'], 0)
        self.assertEqual(session.session_info['start_call'], None)
        self.assertEqual(session.session_info['warnings'], [])
        self.assertEqual(session.session_info['connections'], [])

        events = GenericEvent.objects.filter(
            session=session,
        )

        self.assertEqual(len(session.session_info['gum_warnings']), 3)
        for event in events:
            self.assertTrue({str(event.id): event.data.get('error', {}).get('name')} in session.session_info['gum_warnings'])

        self.assertEqual(len(events), len(responses))

    def test_post_200_addPeer_connected_closed_flow_one_connection(self):

        initial_add_minutes = App.add_minutes
        add_minutes_mock = mock.Mock()
        App.add_minutes = add_minutes_mock

        other_conference = Conference(
            conference_id='test2',
            conference_name='test2',
            app_id=self.app_recording.id
        )
        other_conference.save()

        session = Session(
            participant=self.participant,
            conference=other_conference,
        )

        session.save()

        token = generate_session_token(session)

        addPeer_data = {
            'token': token.decode('utf-8'),
            'eventName': 'addPeer',
            'peerId': 'peer_id',
        }

        self.assertEqual(other_conference.conference_info, Conference.get_default_info())
        self.assertEqual(session.session_info, Session.get_default_info())

        response = self.client.post(
            data=addPeer_data,
            path='/v1/connection',
            content_type='application/json',
        )
        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        peer_id = json.loads(response.content)['peer_id']

        connected_data = {
            'token': token.decode('utf-8'),
            'eventName': 'oniceconnectionstatechange',
            'peerId': peer_id,
            'data': 'connected',
        }

        data = {
            'token': token.decode('utf-8'),
            'eventName': 'oniceconnectionstatechange',
            'peerId': peer_id,
            'data': 'closed',
        }
        session.refresh_from_db()

        self.assertEqual(other_conference.conference_info, Conference.get_default_info())

        self.assertEqual(
            sorted(list(session.session_info.keys())),
            sorted(['warnings', 'call_count', 'start_call', 'connections', 'gum_warnings']),
        )
        self.assertEqual(session.session_info['call_count'], 1)
        self.assertNotEqual(session.session_info['start_call'], None)
        self.assertEqual(session.session_info['warnings'], [])
        self.assertEqual(session.session_info['gum_warnings'], [])
        self.assertEqual(len(session.session_info['connections']), 1)
        self.assertEqual(session.session_info['connections'][0], {
            'type': None,
            'peer_id': peer_id,
            'end_time': None,
            'start_time': session.session_info['start_call'],
            'setup_end_time': None
        })

        response = self.client.post(
            data=connected_data,
            path='/v1/connection',
            content_type='application/json',
        )
        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), '')

        session.refresh_from_db()
        other_conference.refresh_from_db()

        self.assertEqual(
            sorted(list(session.session_info.keys())),
            sorted(['warnings', 'call_count', 'start_call', 'connections', 'gum_warnings']),
        )
        self.assertEqual(session.session_info['call_count'], 1)
        self.assertNotEqual(session.session_info['start_call'], None)
        self.assertEqual(session.session_info['warnings'], [])
        self.assertEqual(session.session_info['gum_warnings'], [])
        self.assertEqual(len(session.session_info['connections']), 1)

        self.assertEqual(session.session_info['connections'][0]['type'], None)
        self.assertEqual(session.session_info['connections'][0]['peer_id'], peer_id)
        self.assertNotEqual(session.session_info['connections'][0]['setup_end_time'], None)
        self.assertEqual(session.session_info['connections'][0]['start_time'], session.session_info['start_call'])
        self.assertEqual(session.session_info['connections'][0]['end_time'], None)

        self.assertEqual(
            sorted(list(other_conference.conference_info.keys())),
            sorted(list(Conference.get_default_info().keys())),
        )
        self.assertNotEqual(other_conference.conference_info['start_time'], None)
        self.assertEqual(other_conference.conference_info['warnings'], [])
        self.assertEqual(other_conference.conference_info['gum_warnings'], [])
        self.assertEqual(other_conference.conference_info['active_connections'], [str(self.participant.id)])

        response = self.client.post(
            data=data,
            path='/v1/connection',
            content_type='application/json',
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), '')

        session.refresh_from_db()
        other_conference.refresh_from_db()

        self.assertEqual(
            sorted(list(session.session_info.keys())),
            sorted(['warnings', 'call_count', 'start_call', 'connections', 'gum_warnings']),
        )
        self.assertEqual(session.session_info['call_count'], 1)
        self.assertEqual(session.session_info['start_call'], None)
        self.assertEqual(session.session_info['warnings'], [])
        self.assertEqual(session.session_info['gum_warnings'], [])
        self.assertEqual(len(session.session_info['connections']), 1)

        self.assertEqual(session.session_info['connections'][0]['type'], None)
        self.assertEqual(session.session_info['connections'][0]['peer_id'], peer_id)
        self.assertNotEqual(session.session_info['connections'][0]['setup_end_time'], None)
        self.assertNotEqual(session.session_info['connections'][0]['start_time'], None)
        self.assertNotEqual(session.session_info['connections'][0]['end_time'], None)

        self.assertEqual(
            sorted(list(other_conference.conference_info.keys())),
            sorted(list(Conference.get_default_info().keys()) + ['had_connection_error']),
        )
        self.assertEqual(other_conference.conference_info['start_time'], None)
        self.assertNotEqual(other_conference.conference_info['close_time'], None)
        self.assertEqual(other_conference.conference_info['warnings'], [])
        self.assertEqual(other_conference.conference_info['gum_warnings'], [])
        self.assertEqual(other_conference.conference_info['active_connections'], [])

        events_no = GenericEvent.objects.filter(
            session=session,
        ).count()

        self.assertEqual(events_no, 3)

        add_minutes_mock.assert_called_once()
        App.add_minutes = initial_add_minutes

    def test_post_200_addPeer_connected_closed_flow_two_connections(self):

        initial_add_minutes = App.add_minutes
        add_minutes_mock = mock.Mock()
        App.add_minutes = add_minutes_mock

        other_conference = Conference(
            conference_id='test2',
            conference_name='test2',
            app_id=self.app_recording.id
        )
        other_conference.save()

        self.participant.conferences.add(other_conference)

        session = Session(
            participant=self.participant,
            conference=other_conference,
        )
        session.save()
        token = generate_session_token(session)


        addPeer_data = {
            'token': token.decode('utf-8'),
            'eventName': 'addPeer',
            'peerId': 'peer_id1',
        }

        addPeer_data2 = {
            'token': token.decode('utf-8'),
            'eventName': 'addPeer',
            'peerId': 'peer_id2',
        }

        self.assertEqual(other_conference.conference_info, Conference.get_default_info())
        self.assertEqual(session.session_info, Session.get_default_info())

        response = self.client.post(
            data=addPeer_data,
            path='/v1/connection',
            content_type='application/json',
        )
        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        peer_id = json.loads(response.content)['peer_id']


        response = self.client.post(
            data=addPeer_data2,
            path='/v1/connection',
            content_type='application/json',
        )
        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        peer_id2 = json.loads(response.content)['peer_id']

        connected_data = {
            'token': token.decode('utf-8'),
            'eventName': 'oniceconnectionstatechange',
            'peerId': peer_id,
            'data': 'connected',
        }


        connected_data2 = {
            'token': token.decode('utf-8'),
            'eventName': 'oniceconnectionstatechange',
            'peerId': peer_id2,
            'data': 'connected',
        }

        data = {
            'token': token.decode('utf-8'),
            'eventName': 'oniceconnectionstatechange',
            'peerId': peer_id,
            'data': 'closed',
        }

        data2 = {
            'token': token.decode('utf-8'),
            'eventName': 'oniceconnectionstatechange',
            'peerId': peer_id2,
            'data': 'closed',
        }
        response = self.client.post(
            data=connected_data,
            path='/v1/connection',
            content_type='application/json',
        )


        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), '')

        response = self.client.post(
            data=connected_data2,
            path='/v1/connection',
            content_type='application/json',
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), '')
        other_conference.refresh_from_db()

        response = self.client.post(
            data=data,
            path='/v1/connection',
            content_type='application/json',
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), '')

        session.refresh_from_db()
        other_conference.refresh_from_db()

        self.assertEqual(
            sorted(list(session.session_info.keys())),
            sorted(['warnings', 'call_count', 'start_call', 'connections', 'gum_warnings']),
        )
        self.assertEqual(session.session_info['call_count'], 1)
        self.assertNotEqual(session.session_info['start_call'], None)
        self.assertEqual(session.session_info['warnings'], [])
        self.assertEqual(session.session_info['gum_warnings'], [])
        self.assertEqual(len(session.session_info['connections']), 2)

        self.assertEqual(session.session_info['connections'][0]['type'], None)
        self.assertEqual(session.session_info['connections'][0]['peer_id'], peer_id2)
        self.assertNotEqual(session.session_info['connections'][0]['setup_end_time'], None)
        self.assertNotEqual(session.session_info['connections'][0]['start_time'], None)
        self.assertEqual(session.session_info['connections'][0]['end_time'], None)

        self.assertEqual(session.session_info['connections'][1]['type'], None)
        self.assertEqual(session.session_info['connections'][1]['peer_id'], peer_id)
        self.assertNotEqual(session.session_info['connections'][1]['setup_end_time'], None)
        self.assertNotEqual(session.session_info['connections'][1]['start_time'], None)
        self.assertNotEqual(session.session_info['connections'][1]['end_time'], None)

        self.assertEqual(
            sorted(list(other_conference.conference_info.keys())),
            sorted(list(Conference.get_default_info().keys()) + ['had_connection_error']),
        )
        self.assertEqual(other_conference.conference_info['start_time'], None)
        self.assertNotEqual(other_conference.conference_info['close_time'], None)
        self.assertEqual(other_conference.conference_info['warnings'], [])
        self.assertEqual(other_conference.conference_info['gum_warnings'], [])
        self.assertEqual(other_conference.conference_info['active_connections'], [])

        add_minutes_mock.assert_not_called()

        response = self.client.post(
            data=data2,
            path='/v1/connection',
            content_type='application/json',
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), '')

        session.refresh_from_db()
        other_conference.refresh_from_db()

        self.assertEqual(
            sorted(list(session.session_info.keys())),
            sorted(['warnings', 'call_count', 'start_call', 'connections', 'gum_warnings']),
        )
        self.assertEqual(session.session_info['call_count'], 1)
        self.assertEqual(session.session_info['start_call'], None)
        self.assertEqual(session.session_info['warnings'], [])
        self.assertEqual(session.session_info['gum_warnings'], [])
        self.assertEqual(len(session.session_info['connections']), 2)

        self.assertEqual(session.session_info['connections'][0]['type'], None)
        self.assertEqual(session.session_info['connections'][0]['peer_id'], peer_id2)
        self.assertNotEqual(session.session_info['connections'][0]['setup_end_time'], None)
        self.assertNotEqual(session.session_info['connections'][0]['start_time'], None)
        self.assertNotEqual(session.session_info['connections'][0]['end_time'], None)

        self.assertEqual(session.session_info['connections'][1]['type'], None)
        self.assertEqual(session.session_info['connections'][1]['peer_id'], peer_id)
        self.assertNotEqual(session.session_info['connections'][1]['setup_end_time'], None)
        self.assertNotEqual(session.session_info['connections'][1]['start_time'], None)
        self.assertNotEqual(session.session_info['connections'][1]['end_time'], None)

        self.assertEqual(
            sorted(list(other_conference.conference_info.keys())),
            sorted(list(Conference.get_default_info().keys()) + ['had_connection_error']),
        )
        self.assertEqual(other_conference.conference_info['start_time'], None)
        self.assertNotEqual(other_conference.conference_info['close_time'], None)
        self.assertEqual(other_conference.conference_info['warnings'], [])
        self.assertEqual(other_conference.conference_info['gum_warnings'], [])
        self.assertEqual(other_conference.conference_info['active_connections'], [])

        events_no = GenericEvent.objects.filter(
            session=session,
        ).count()

        self.assertEqual(events_no, 6)

        add_minutes_mock.assert_called_once()
        App.add_minutes = initial_add_minutes

    def test_post_200_addPeer_connected_unload_flow_one_connection(self):

        initial_add_minutes = App.add_minutes
        add_minutes_mock = mock.Mock()
        App.add_minutes = add_minutes_mock

        other_conference = Conference(
            conference_id='test2',
            conference_name='test2',
            app_id=self.app_recording.id
        )
        other_conference.save()

        session = Session(
            participant=self.participant,
            conference=other_conference,
        )

        session.save()

        token = generate_session_token(session)

        addPeer_data = {
            'token': token.decode('utf-8'),
            'eventName': 'addPeer',
            'peerId': 'peer_id',
        }

        self.assertEqual(other_conference.conference_info, Conference.get_default_info())
        self.assertEqual(session.session_info, Session.get_default_info())

        response = self.client.post(
            data=addPeer_data,
            path='/v1/connection',
            content_type='application/json',
        )
        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        peer_id = json.loads(response.content)['peer_id']

        connected_data = {
            'token': token.decode('utf-8'),
            'eventName': 'oniceconnectionstatechange',
            'peerId': peer_id,
            'data': 'connected',
        }

        data = {
            'token': token.decode('utf-8'),
            'eventName': 'unload',
        }

        session.refresh_from_db()

        self.assertEqual(other_conference.conference_info, Conference.get_default_info())

        self.assertEqual(
            sorted(list(session.session_info.keys())),
            sorted(['warnings', 'call_count', 'start_call', 'connections', 'gum_warnings']),
        )
        self.assertEqual(session.session_info['call_count'], 1)
        self.assertNotEqual(session.session_info['start_call'], None)
        self.assertEqual(session.session_info['warnings'], [])
        self.assertEqual(session.session_info['gum_warnings'], [])
        self.assertEqual(len(session.session_info['connections']), 1)
        self.assertEqual(session.session_info['connections'][0], {
            'type': None,
            'peer_id': peer_id,
            'end_time': None,
            'start_time': session.session_info['start_call'],
            'setup_end_time': None
        })

        response = self.client.post(
            data=connected_data,
            path='/v1/connection',
            content_type='application/json',
        )
        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), '')

        session.refresh_from_db()
        other_conference.refresh_from_db()

        self.assertEqual(
            sorted(list(session.session_info.keys())),
            sorted(['warnings', 'call_count', 'start_call', 'connections', 'gum_warnings']),
        )
        self.assertEqual(session.session_info['call_count'], 1)
        self.assertNotEqual(session.session_info['start_call'], None)
        self.assertEqual(session.session_info['warnings'], [])
        self.assertEqual(session.session_info['gum_warnings'], [])
        self.assertEqual(len(session.session_info['connections']), 1)

        self.assertEqual(session.session_info['connections'][0]['type'], None)
        self.assertEqual(session.session_info['connections'][0]['peer_id'], peer_id)
        self.assertNotEqual(session.session_info['connections'][0]['setup_end_time'], None)
        self.assertEqual(session.session_info['connections'][0]['start_time'], session.session_info['start_call'])
        self.assertEqual(session.session_info['connections'][0]['end_time'], None)

        self.assertEqual(
            sorted(list(other_conference.conference_info.keys())),
            sorted(list(Conference.get_default_info().keys())),
        )
        self.assertNotEqual(other_conference.conference_info['start_time'], None)
        self.assertEqual(other_conference.conference_info['warnings'], [])
        self.assertEqual(other_conference.conference_info['gum_warnings'], [])
        self.assertEqual(other_conference.conference_info['active_connections'], [str(self.participant.id)])

        response = self.client.post(
            data=data,
            path='/v1/events/browser',
            content_type='application/json',
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), '')

        session.refresh_from_db()
        other_conference.refresh_from_db()

        self.assertEqual(
            sorted(list(session.session_info.keys())),
            sorted(['warnings', 'call_count', 'start_call', 'connections', 'gum_warnings']),
        )
        self.assertEqual(session.session_info['call_count'], 1)
        self.assertEqual(session.session_info['start_call'], None)
        self.assertEqual(session.session_info['warnings'], [])
        self.assertEqual(session.session_info['gum_warnings'], [])
        self.assertEqual(len(session.session_info['connections']), 1)

        self.assertEqual(session.session_info['connections'][0]['type'], None)
        self.assertEqual(session.session_info['connections'][0]['peer_id'], peer_id)
        self.assertNotEqual(session.session_info['connections'][0]['setup_end_time'], None)
        self.assertNotEqual(session.session_info['connections'][0]['start_time'], None)
        self.assertNotEqual(session.session_info['connections'][0]['end_time'], None)

        self.assertEqual(
            sorted(list(other_conference.conference_info.keys())),
            sorted(list(Conference.get_default_info().keys()) + ['had_connection_error']),
        )
        self.assertEqual(other_conference.conference_info['start_time'], None)
        self.assertNotEqual(other_conference.conference_info['close_time'], None)
        self.assertEqual(other_conference.conference_info['warnings'], [])
        self.assertEqual(other_conference.conference_info['gum_warnings'], [])
        self.assertEqual(other_conference.conference_info['active_connections'], [])

        events_no = GenericEvent.objects.filter(
            session=session,
        ).count()

        self.assertEqual(events_no, 3)

        add_minutes_mock.assert_called_once()
        App.add_minutes = initial_add_minutes

    def test_post_200_addPeer_connected_unload_flow_two_connections(self):

        initial_add_minutes = App.add_minutes
        add_minutes_mock = mock.Mock()
        App.add_minutes = add_minutes_mock

        other_conference = Conference(
            conference_id='test2',
            conference_name='test2',
            app_id=self.app_recording.id
        )
        other_conference.save()

        session = Session(
            participant=self.participant,
            conference=other_conference,
        )

        session.save()

        token = generate_session_token(session)

        addPeer_data = {
            'token': token.decode('utf-8'),
            'eventName': 'addPeer',
            'peerId': 'peer_id',
        }

        addPeer_data2 = {
            'token': token.decode('utf-8'),
            'eventName': 'addPeer',
            'peerId': 'peer_id2',
        }

        self.assertEqual(other_conference.conference_info, Conference.get_default_info())
        self.assertEqual(session.session_info, Session.get_default_info())

        response = self.client.post(
            data=addPeer_data,
            path='/v1/connection',
            content_type='application/json',
        )
        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        peer_id = json.loads(response.content)['peer_id']

        response = self.client.post(
            data=addPeer_data2,
            path='/v1/connection',
            content_type='application/json',
        )
        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        peer_id2 = json.loads(response.content)['peer_id']

        connected_data = {
            'token': token.decode('utf-8'),
            'eventName': 'oniceconnectionstatechange',
            'peerId': peer_id,
            'data': 'connected',
        }

        connected_data2 = {
            'token': token.decode('utf-8'),
            'eventName': 'oniceconnectionstatechange',
            'peerId': peer_id2,
            'data': 'connected',
        }

        data = {
            'token': token.decode('utf-8'),
            'eventName': 'unload',
        }

        response = self.client.post(
            data=connected_data,
            path='/v1/connection',
            content_type='application/json',
        )
        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), '')

        response = self.client.post(
            data=connected_data2,
            path='/v1/connection',
            content_type='application/json',
        )
        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), '')

        response = self.client.post(
            data=data,
            path='/v1/events/browser',
            content_type='application/json',
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), '')

        session.refresh_from_db()
        other_conference.refresh_from_db()

        self.assertEqual(
            sorted(list(session.session_info.keys())),
            sorted(['warnings', 'call_count', 'start_call', 'connections', 'gum_warnings']),
        )
        self.assertEqual(session.session_info['call_count'], 1)
        self.assertEqual(session.session_info['start_call'], None)
        self.assertEqual(session.session_info['warnings'], [])
        self.assertEqual(session.session_info['gum_warnings'], [])
        self.assertEqual(len(session.session_info['connections']), 2)

        self.assertEqual(session.session_info['connections'][0]['type'], None)
        self.assertEqual(session.session_info['connections'][0]['peer_id'], peer_id2)
        self.assertNotEqual(session.session_info['connections'][0]['setup_end_time'], None)
        self.assertNotEqual(session.session_info['connections'][0]['start_time'], None)
        self.assertNotEqual(session.session_info['connections'][0]['end_time'], None)

        self.assertEqual(session.session_info['connections'][1]['type'], None)
        self.assertEqual(session.session_info['connections'][1]['peer_id'], peer_id)
        self.assertNotEqual(session.session_info['connections'][1]['setup_end_time'], None)
        self.assertNotEqual(session.session_info['connections'][1]['start_time'], None)
        self.assertNotEqual(session.session_info['connections'][1]['end_time'], None)

        self.assertEqual(
            sorted(list(other_conference.conference_info.keys())),
            sorted(list(Conference.get_default_info().keys()) + ['had_connection_error']),
        )
        self.assertEqual(other_conference.conference_info['start_time'], None)
        self.assertNotEqual(other_conference.conference_info['close_time'], None)
        self.assertEqual(other_conference.conference_info['warnings'], [])
        self.assertEqual(other_conference.conference_info['gum_warnings'], [])
        self.assertEqual(other_conference.conference_info['active_connections'], [])

        events_no = GenericEvent.objects.filter(
            session=session,
        ).count()

        self.assertEqual(events_no, 5)

        add_minutes_mock.assert_called_once()
        App.add_minutes = initial_add_minutes

    def get_all(self, data, **kwargs):
        return [
            (self.client.get(path=url, data=data, **kwargs), self.get_urls[url])
            for url in self.get_urls.keys()
        ]

    def test_get_missing_parameters(self):

        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )
        self.create_subscription(user)

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        responses = self.get_all(
            data={},
            content_type='application/json',
        )

        for response in responses:
            response = response[0]
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
            ('1', '1', CONFERENCE_NOT_FOUND),
            ('1asdasd', '', CONFERENCE_NOT_FOUND),
            ('', '1', PARTICIPANT_NOT_FOUND),
            ('', 'dasdasd1', PARTICIPANT_NOT_FOUND),
            (str(uuid.uuid4()), '1', CONFERENCE_NOT_FOUND),
            ('', str(uuid.uuid4()), PARTICIPANT_NOT_FOUND),
            (str(self.conference.id), str(uuid.uuid4()), PARTICIPANT_NOT_FOUND),
            (str(self.conference.id), participant_not_active.id, PARTICIPANT_NOT_FOUND),
            (str(uuid.uuid4()), str(self.participant.id), CONFERENCE_NOT_FOUND),
            (conference_not_active.id, str(self.participant.id), CONFERENCE_NOT_FOUND),
            (str(uuid.uuid4()), str(uuid.uuid4()), CONFERENCE_NOT_FOUND),
        ]

        for inp in inputs:

            data = {
                'conferenceId': inp[0],
                'participantId': inp[1],
            }
            expected_error = inp[2]

            responses = self.get_all(data=data)

            for response in responses:
                response = response[0]
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
            (self.conference.id, '', CONFERENCE_NOT_FOUND),
            ('', self.participant.id, PARTICIPANT_NOT_FOUND),
        ]

        for inp in inputs:

            data = {
                'conferenceId': inp[0],
                'participantId': inp[1],
            }
            expected_error = inp[2]

            responses = self.get_all(data=data)

            for response in responses:
                response = response[0]
                self.assertTrue(isinstance(response, JSONHttpResponse))
                self.assertEqual(response.status_code, 400)
                self.assertEqual(json.loads(response.content), expected_error)

        self.client.logout()

    def test_get_200(self):
        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )
        self.create_subscription(user)
        self.assertTrue(self.client.login(username=user.username, password=user_password))

        self.org.members.add(user)
        self.org.save()

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

        session = Session(
            conference=self.conference,
            participant=self.participant,
            metadata='test1',
        )
        session.save()

        session = Session(
            conference=other_conference,
            participant=self.participant,
            metadata='test1',
        )
        session.save()

        session = Session(
            conference=self.conference,
            participant=other_participant,
            metadata='test1',
        )
        session.save()

        inputs = [
            {
                'data': {
                    'conferenceId': str(self.conference.id),
                },
                'base_filter': {
                    'conference': self.conference,
                }
            },
            {
                'data': {
                    'participantId': str(self.participant.id),
                },
                'base_filter': {
                    'participant': self.participant,
                }
            },
            {
                'data': {
                    'conferenceId': str(self.conference.id),
                    'participantId': str(self.participant.id),
                },
                'base_filter': {
                    'conference': self.conference,
                    'participant': self.participant,
                }
            },
            {
                'data': {
                    'conferenceId': str(other_conference.id),
                },
                'base_filter': {
                    'conference': other_conference,
                }
            },
            {
                'data': {
                    'conferenceId': str(other_conference.id),
                    'participantId': str(other_participant.id),
                },
                'base_filter': {
                    'conference': other_conference,
                    'participant': other_participant,
                }
            },
        ]

        for event_type in settings.EVENT_CATEGORIES.keys():
            GenericEvent(
                participant=self.participant,
                conference=self.conference,
                session=session,
                app=self.app_recording,
                category=settings.EVENT_CATEGORIES.get(event_type),
                type='type_{}'.format(event_type),
                peer_id=str(self.participant.id),
                data='data_{}'.format(event_type),
            ).save()
            GenericEvent(
                participant=other_participant,
                conference=other_conference,
                session=session,
                app=self.app_recording,
                category=settings.EVENT_CATEGORIES.get(event_type),
                type='type_{}'.format(event_type),
                peer_id=str(self.participant.id),
                data='data_{}'.format(event_type),
            ).save()

        for inp in inputs:

            responses = self.get_all(data=inp['data'])
            base_filter = inp['base_filter']

            for response in responses:
                t = response[1]
                response = response[0]

                filters = {'category': settings.EVENT_CATEGORIES[t]}
                filters.update(base_filter)

                expected = serialize(GenericEvent.filter(**filters))
                self.assertTrue(isinstance(response, JSONHttpResponse))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(json.loads(response.content.decode('utf-8')), expected)

        self.client.logout()
