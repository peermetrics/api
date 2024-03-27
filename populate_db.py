#!/usr/bin/env python

import datetime
import random
import uuid
import json
import os
import sys
import itertools
import importlib

import django
django.setup()

from django.utils import timezone
from django.conf import settings
from django.test import Client

import jwt

from app.models.organization import Organization
from app.models.app import App
from app.models.participant import Participant
from app.models.conference import Conference

from config_populate_db.session_data import DEVICES, PLATFORMS
from config_populate_db.geo_ip_data import GEO_IP_HEADERS

client = Client()

first = (
    'Super', 'Great', 'Brave',
    'Shy', 'Cool', 'Rich', 'Fast', 'Gummy', 'Yummy',
    'Masked', 'Unusual', 'MLG', 'Mlg', 'Lil',
)
second = (
    'Coder', 'Hacker', 'Horse', 'Bear', 'Goat',
    'Goblin', 'Learner', 'Killer', 'Programmer', 'Spy',
    'Carrot', 'Goat', 'Quickscoper',
)


def prob(abi, l):
    return list(itertools.chain.from_iterable([[el for _ in range(l[i])] for i, el in enumerate(abi)]))

def create_participant(app):
    participant = Participant(
        participant_id=str(uuid.uuid4()),
        participant_name=''.join([random.choice(first), ' ', random.choice(second)]),
        app_id=app.id,
    )
    participant.save()

    return participant


def create_conference(app, now):
    global conference_count
    conference_count += 1
    conference = Conference(
        conference_id=''.join(['conference-', str(conference_count)]),
        conference_name=''.join(['Conference ', str(conference_count)]),
        app_id=app.id,
        created_at=now,
    )
    conference.save()

    return conference


def get_event_request_body(
        token, event_data, event_name,
        peer, connection_id, delta, now=datetime.datetime.utcnow(),
):
    data = {
        'token': token,
        'delta': (datetime.datetime.utcnow() - now).total_seconds() * 1000 - delta,
        'connectionId': connection_id,
        'peerId': peer,
        'data': event_data,
        'eventName': event_name,
    }

    return data


def get_stats_event_request_body(
        token, event_data, event_name,
        peer, connection_id, delta, now=datetime.datetime.utcnow(),
):
    data = {
        'token': token,
        'delta': (datetime.datetime.utcnow() - now).total_seconds() * 1000 - delta,
        'connectionId': connection_id,
        'peerId': peer,
        'data': event_data,
        'eventName': event_name,
    }

    return data


def create_event_call(data):
    response = client.post(
        data=data,
        path='/v1/events/browser',
        content_type='application/json',
    )

    assert response.status_code == 200

    return json.loads(response.content.decode('utf-8'))


def create_stats_event_call(data):
    response = client.post(
        data=data,
        path='/v1/stats',
        content_type='application/json',
    )
    assert response.status_code == 200


def create_session_call(conference, participant, session_data, now):
    payload = {
        'p': str(participant.id),
        'c': str(conference.id),
        't': datetime.datetime.utcnow().timestamp(),
    }

    token = jwt.encode(
        payload=payload,
        key=settings.INIT_TOKEN_SECRET,
        algorithm='HS256',
    )

    if session_data and session_data['geo_ip'] and session_data['geo_ip']['latitude']:
        geo_ip_data = {
            'X-AppEngine-City': session_data['geo_ip']['city'],
            'X-AppEngine-Country': session_data['geo_ip']['country_code'],
            'X-AppEngine-CityLatLong': ''.join([
                str(session_data['geo_ip']['latitude']),
                ',',
                str(session_data['geo_ip']['longitude']),
            ]),
        }
    else:
        geo_ip_data = random.choice(GEO_IP_HEADERS)
        session_data = {
            'constraints': ('constraints',),
            'devices': {
                'deviceId': random.choice(DEVICES['deviceId']),
                'kind': random.choice(DEVICES['kind']),
                'label': random.choice(DEVICES['label']),
            },
            'platform': random.choice(prob(PLATFORMS, [6, 3, 1, 6, 3, 1])),
            'meta': {'meta': 'meta'},
            'app_version': '0.0.1',
            'delta': (datetime.datetime.utcnow() - now).total_seconds() * 1000,
        }

    response = client.post(
        path='/v1/sessions',
        data={
            'token': token.decode('utf-8'),
            **session_data,
        },
        content_type='application/json',
        **geo_ip_data,
    )

    assert response.status_code == 200

    token = json.loads(response.content.decode('utf-8'))['token']

    return token


def setup():
    """
    Create the test org and app
    """

    org, org_created = Organization(
        name='test_org',
        created_at=timezone.now() - timezone.timedelta(days=15),
    ).get_or_create()


    try:
        app = App.objects.get(name="test app", organization=org, is_active=True)
    except App.DoesNotExist:
        app = App(
            api_key=str(uuid.uuid4()).replace('-', ''),
            organization=org,
            name='test app',
            created_at=timezone.now() - timezone.timedelta(days=15),
        )
        app.save()

    return app


def populate(app, participant_list, day, events, no_participants, sessions_data):

    # subtract the day, so we go in the past
    now = timezone.now() - timezone.timedelta(days=day)

    conference = create_conference(app, now)

    participants = random.sample(participant_list, no_participants)

    connection_ids = [None, None]

    for participant in participants:
        participant.conferences.add(conference)

    # create sessions for these participants

    tokens = [
        create_session_call(conference, participant, sessions_data.get(idx), now)
        for idx, participant in enumerate(participants)
    ]

    t0 = None
    using_deltas = False
    for event in events:
        if t0 is None:
            if event.get('delta') is not None:
                using_deltas = True
            t0 = now

        if event.get('eventName') == 'stats':
            create_stats_event_call(get_stats_event_request_body(
                token=tokens[event['participant']],
                event_data=event['data'],
                event_name=event['eventName'],
                peer=str(participants[event['peer']]) if event['peer'] is not None else None,
                connection_id=connection_ids[event['participant']],
                delta=event['delta'] if event.get('delta') is not None else 0,
                now=now,
            ))
        else:
            res = create_event_call(get_event_request_body(
                token=tokens[event['participant']],
                event_data=event['data'],
                event_name=event['eventName'],
                peer=str(participants[event['peer']]) if event['peer'] is not None else None,
                connection_id=connection_ids[event['participant']],
                delta=event['delta'] if event.get('delta') is not None else 0,
                now=now,
            ))

            if event.get('eventName') == 'addConnection':
                connection_ids[event['participant']] = res.get('connection_id')

        if not using_deltas:
            now = now + timezone.timedelta(milliseconds=random.randint(0, 100))


def clean():
    try:
        Organization.get(name='test_org').delete()
        print('Your db is squeaky clean!')
    except Exception as exc:
        print('Nothing to clean!')
        print(exc)


def show_instructions():
    print('Usage:')
    print('./populate_db.py clean / <int> ')
    print('\tclean - deletes everything that this script created in the db')
    print('\t<int> - runs the script for a specific number of days starting from today (num > 1)')


def run(days, input_modules):
    created = 0
    global input_module

    app = setup()
    if not app:
        raise Exception('Could not find app for test user')

    if days < 1:
        raise Exception('days should be more than 1')

    participants = [create_participant(app) for _ in range(15)]

    for day in range(1, days + 1):
        # anywhere between 3 and 7 calls for this day
        number_of_calls = random.randint(3, 7)

        for call in range(number_of_calls):
            input_module = random.choice(input_modules)

            kwargs = {
                'app': app,
                'participant_list': participants,
                'day': day,
                'events': input_module.EVENTS,
                'no_participants': 2
            }
            try:
                sessions_data = input_module.SESSION_DATA
                kwargs['sessions_data'] = sessions_data
            except AttributeError:
                kwargs['sessions_data'] = {}
            populate(**kwargs)

        created += number_of_calls

    print('Created ' + str(created) + ' call!')


if __name__ == '__main__':

    global input_module
    global conference_count
    conference_count = 0
    input_module = None
    if len(sys.argv) not in (2, 3):
        show_instructions()
    else:
        # if the argument is 'clean', clear the db
        if str(sys.argv[1]) == 'clean':
            clean()
        else:
            if len(sys.argv) == 3:
                input_file = sys.argv[2]
                input_modules = [importlib.import_module(input_file)]
            else:
                input_modules = [
                    importlib.import_module(''.join(['config_populate_db.used_events.', file[:-3]]))
                    for file in os.listdir(os.path.join('config_populate_db', 'used_events'))
                    if file.endswith('.py') and file != '__init__.py'
                ]
            try:
                n = int(sys.argv[1])
            except Exception:
                show_instructions()
            else:
                run(n, input_modules)
