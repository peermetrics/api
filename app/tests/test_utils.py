import datetime

from .classes import PMTestCase
from ..utils import serialize
from ..models.generic_event import GenericEvent
from ..models.session import Session
from ..models.token import Token

from django.conf import settings


class UtilsTestCase(PMTestCase):

    def test_serialize_user(self):
        self.user.notifications = {
            'test': {
                1: 17,
            }
        }
        self.user.save()
        self.assertEqual(
            serialize(
                [self.user, self.user],
                whitelist=(
                    'id', 'last_active', 'billing', 'notifications',
                    'is_verified', 'max_usage', 'usage',
                    'subscription',
                ),
                expand_fields=('subscription', )
            ),
            {
                'data': [
                    {
                        'subscription': str(self.user.subscription.id),
                        'id': str(self.user.id),
                        'last_active': str(self.user.last_active),
                        'billing': self.user.billing,
                        'notifications': self.user.notifications,
                        'is_verified': self.user.is_verified,
                        'max_usage': self.user.max_usage,
                        'usage': self.user.usage,
                    },
                    {
                        'subscription': str(self.user.subscription.id),
                        'id': str(self.user.id),
                        'last_active': str(self.user.last_active),
                        'billing': self.user.billing,
                        'notifications': self.user.notifications,
                        'is_verified': self.user.is_verified,
                        'max_usage': self.user.max_usage,
                        'usage': self.user.usage,
                    },
                ],
            },
        )
        self.user.notifications = {}
        self.user.save()

    def test_serialize_subscription(self):
        self.assertEqual(
            serialize(
                [self.user.subscription],
            ),
            {
                'data': [
                    {
                        'id': str(self.user.subscription.id),
                        'user': str(self.user.subscription.user.id),
                        'price': str(self.user.subscription.price),
                        'currency': self.user.subscription.currency,
                        'subscription_id': self.user.subscription.subscription_id,
                        'subscription_item_id': self.user.subscription.subscription_item_id,
                        'customer_id': self.user.subscription.customer_id,
                        'has_card_attached': False,
                        'status': self.user.subscription.status,
                        'plan_id': self.user.subscription.plan_id,
                        'first_billing_date': str(self.user.subscription.first_billing_date),
                        'current_period_end': str(self.user.subscription.current_period_end),
                        'current_period_start': str(self.user.subscription.current_period_start),
                        'current_billing_cycle': self.user.subscription.current_billing_cycle,
                        'created_at': str(self.user.subscription.created_at),
                        'last_modified': str(self.user.subscription.last_modified),
                    },
                ],
            },
        )

    def test_serialize_organization(self):
        self.assertEqual(
            serialize(
                [self.org],
                expand_fields=('members', 'apps'),
            ),
            {
                'data': [
                    {
                        'apps': [str(app.id) for app in self.org.apps.all().order_by('created_at')],
                        'created_at': str(self.org.created_at),
                        'id': str(self.org.id),
                        'members': [str(m.id) for m in self.org.members.all().order_by('-created_at')],
                        'name': self.org.name,
                        'owner': str(self.org.owner_id),
                    },
                ],
            },
        )

    def test_serialize_token(self):
        token = Token(
            user=self.user,
            usage='test',
            token='test token',
            expiration_date=datetime.datetime.utcnow(),
        )

        self.assertEqual(
            serialize(
                [token],
            ),
            {
                'data': [
                    {
                        'expiration_date': str(token.expiration_date),
                        'id': str(token.id),
                        'token': token.token,
                        'usage': token.usage,
                        'user': str(token.user_id),
                        'data': {},
                    },
                ],
            },
        )

    def test_serialize_app(self):
        self.assertEqual(
            serialize(
                [self.app_recording, self.app_not_recording],
                expand_fields=('conferences', 'participants', 'events'),
            ),
            {
                'data': [
                    {
                        'created_at': str(self.app_recording.created_at),
                        'id': str(self.app_recording.id),
                        'name': self.app_recording.name,
                        'interval': self.app_recording.interval,
                        'recording': self.app_recording.recording,
                        'api_key': self.app_recording.api_key,
                        'durations_days': self.app_recording.durations_days,
                        'domain': self.app_recording.domain,
                        'organization': str(self.app_recording.organization_id),
                        'conferences': [str(c.id) for c in self.app_recording.conferences.all().order_by('-created_at')],
                        'participants': [str(p.id) for p in self.app_recording.participants.all().order_by('created_at')],
                        'events': [str(e.id) for e in self.app_recording.events.all().order_by('-created_at')],
                    },
                    {
                        'created_at': str(self.app_not_recording.created_at),
                        'id': str(self.app_not_recording.id),
                        'name': self.app_not_recording.name,
                        'interval': self.app_not_recording.interval,
                        'recording': self.app_not_recording.recording,
                        'api_key': self.app_not_recording.api_key,
                        'durations_days': self.app_not_recording.durations_days,
                        'domain': self.app_not_recording.domain,
                        'organization': str(self.app_not_recording.organization_id),
                        'conferences': [str(c.id) for c in self.app_not_recording.conferences.all().order_by('-created_at')],
                        'participants': [str(p.id) for p in self.app_not_recording.participants.all().order_by('created_at')],
                        'events': [str(e.id) for e in self.app_not_recording.events.all().order_by('-created_at')],
                    },
                ],
            },
        )

    def test_serialize_conference(self):
        self.assertEqual(
            serialize(
                [self.conference],
                expand_fields=('sessions', 'participants', 'events'),
            ),
            {
                'data': [
                    {
                        'created_at': str(self.conference.created_at),
                        'id': str(self.conference.id),
                        'conference_info': self.conference.conference_info,
                        'conference_id': self.conference.conference_id,
                        'conference_name': self.conference.conference_name,
                        'participants': [str(p.id) for p in self.conference.participants.all().order_by('created_at')],
                        'sessions': [str(p.id) for p in self.conference.sessions.all().order_by('-created_at')],
                        'app': str(self.conference.app_id),
                        'events': [str(e.id) for e in self.conference.events.all().order_by('-created_at')],
                    },
                ],
            },
        )

    def test_serialize_participant(self):
        self.assertEqual(
            serialize(
                [self.participant],
                expand_fields=('sessions', 'conferences', 'events'),
            ),
            {
                'data': [
                    {
                        'created_at': str(self.participant.created_at),
                        'id': str(self.participant.id),
                        'participant_id': self.participant.participant_id,
                        'participant_name': self.participant.participant_name,
                        'conferences': [str(p.id) for p in self.participant.conferences.all().order_by('-created_at')],
                        'sessions': [str(p.id) for p in self.participant.sessions.all().order_by('-created_at')],
                        'app': str(self.participant.app_id),
                        'events': [str(e.id) for e in self.participant.events.all().order_by('-created_at')],
                    },
                ],
            },
        )

    def test_serialize_session_and_generic_event(self):
        session = Session(
            participant=self.participant,
            conference=self.conference,
            app_version='0.0.1',
            platform={
                'ua': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.70 Safari/537.36',
                'browser': {
                    'name': 'Chrome',
                    'version': '78.0.3904.70',
                    'major': '78'},
                'engine': {
                    'name': 'Blink',
                },
                'os': {
                    'name': 'Windows',
                    'version': '10',
                },
                'device': {},
                'cpu': {
                    'architecture': 'amd64',
                },
            },
            devices={
                'deviceId': '3b04c0489408f0fb423895071d74f83b03fc6211754a492509916864feb1fa1e',
                'kind': 'audioinput',
                'label': 'Creative Headset',
            },
            geo_ip={
                'country_code': 'US',
                'city': 'San Jose',
                'latitude': '37.34217071533203',
                'longitude': '-121.90677642822266',
            },
        )
        session.save()

        event = GenericEvent(
            participant=self.participant,
            conference=self.conference,
            session=session,
            app=self.app_recording,
            category=settings.EVENT_CATEGORIES.get('getUserMedia'),
            type='getUserMedia',
            data={
                'audio': {
                    'enabled': True,
                    'id': '0f39fdbe-90a8-4843-9c47-3dafc8157843',
                    'contentHint': '',
                    'kind': 'audio',
                    'label': 'Default',
                    'muted': False,
                    'readyState': 'live',
                    'constructorName': 'MediaStreamTrack',
                    'capabilities': {
                        'autoGainControl': [
                            True,
                            False,
                        ],
                        'channelCount': {
                            'max': 2,
                            'min': 1,
                        },
                        'deviceId': 'default',
                        'echoCancellation': [
                            True,
                            False,
                        ],
                        'groupId': '9fddadbfc3ea2e172ba2f05d36a0570cc9f1fa9cdb481eaa19c18ec6182ab43b',
                        'latency': {
                            'max': 0.023219,
                            'min': 0.01,
                        },
                        'noiseSuppression': [
                            True,
                            False,
                        ],
                        'sampleRate': {
                            'max': 48000,
                            'min': 44100,
                        },
                        'sampleSize': {
                            'max': 16,
                            'min': 16,
                        },
                    },
                    'constraints': {},
                    'settings': {
                        'autoGainControl': True,
                        'channelCount': 1,
                        'deviceId': 'default',
                        'echoCancellation': True,
                        'groupId': '9fddadbfc3ea2e172ba2f05d36a0570cc9f1fa9cdb481eaa19c18ec6182ab43b',
                        'latency': 0.01,
                        'noiseSuppression': True,
                        'sampleRate': 48000,
                        'sampleSize': 16,
                    },
                    '_track': {},
                },
                'video': {
                    'enabled': True,
                    'id': 'f48af77d-37fe-4ec4-be9d-f8d91e972ef6',
                    'contentHint': '',
                    'kind': 'video',
                    'label': 'Integrated Webcam (1bcf: 28b8)',
                    'muted': False,
                    'readyState': 'live',
                    'constructorName': 'MediaStreamTrack',
                    'capabilities': {
                        'aspectRatio': {
                            'max': 1280,
                            'min': 0.001388888888888889,
                        },
                        'deviceId': '44f796ccf1e9b0d3f356084c9ea3d5f9cdc47e8b211e4b5a9b1ed00b1621f008',
                        'facingMode': [],
                        'frameRate': {
                            'max': 30,
                            'min': 0,
                        },
                        'groupId': '338abd3b8976cacd4dd057343de4ce2aa9050e9432750807890ad1683170f9cd',
                        'height': {
                            'max': 720,
                            'min': 1,
                        },
                        'resizeMode': [
                            'none',
                            'crop-and-scale',
                        ],
                        'width': {
                            'max': 1280,
                            'min': 1,
                        },
                    },
                    'constraints': {},
                    'settings': {
                        'aspectRatio': 1.3333333333333333,
                        'deviceId': '44f796ccf1e9b0d3f356084c9ea3d5f9cdc47e8b211e4b5a9b1ed00b1621f008',
                        'frameRate': 30,
                        'groupId': '338abd3b8976cacd4dd057343de4ce2aa9050e9432750807890ad1683170f9cd',
                        'height': 480,
                        'resizeMode': 'none',
                        'width': 640,
                    },
                    '_track': {},
                }
            }
        )

        self.assertEqual(
            serialize(
                [session, event],
                expand_fields=('events', ),
            ),
            {
                'data': [
                    {
                        'created_at': str(session.created_at),
                        'id': str(session.id),
                        'participant': str(session.participant_id),
                        'conference': str(session.conference_id),
                        'constraints': session.constraints,
                        'devices': session.devices,
                        'platform': session.platform,
                        'metadata': session.metadata,
                        'geo_ip': session.geo_ip,
                        'app_version': session.app_version,
                        'duration': session.duration,
                        'session_info': session.session_info,
                        'events': [str(e.id) for e in session.events.all().order_by('-created_at')],
                    },
                    {
                        'created_at': str(event.created_at),
                        'id': str(event.id),
                        'type': event.type,
                        'category': event.category,
                        'peer': str(event.peer_id) if event.peer else None,
                        'data': event.data,
                        'participant': str(event.participant_id),
                        'conference': str(event.conference_id),
                        'session': str(event.session_id),
                        'app': str(event.app_id),
                    },
                ],
            },
        )

    def test_serialize_blacklist(self):
        self.assertEqual(
            serialize(
                [self.org],
                blacklist=('created_at', 'name', 'is_active'),
                expand_fields=('members', 'apps'),
            ),
            {
                'data': [
                    {
                        'apps': [str(app.id) for app in self.org.apps.all().order_by('created_at')],
                        'id': str(self.org.id),
                        'members': [str(m.id) for m in self.org.members.all().order_by('-created_at')],
                        'owner': str(self.org.owner_id),
                    },
                ],
            },
        )

    def test_serialize_whitelist(self):
        self.assertEqual(
            serialize(
                [self.org],
                whitelist=('members', 'owner'),
                expand_fields=('members', ),
            ),
            {
                'data': [
                    {
                        'members': [str(m.id) for m in self.org.members.all().order_by('-created_at')],
                        'owner': str(self.org.owner_id),
                    },
                ],
            },
        )

    def test_serialize_whitelist_and_blacklist(self):
        self.assertEqual(
            serialize(
                [self.org],
                whitelist=('members', 'owner'),
                blacklist=('apps', 'owner', 'is_active'),
                expand_fields=('members', ),
            ),
            {
                'data': [
                    {
                        'members': [str(m.id) for m in self.org.members.all().order_by('-created_at')],
                    },
                ],
            },
        )

    def test_serialize_single_object(self):
        self.assertEqual(
            serialize(
                [self.org],
                return_single_object=True,
                expand_fields=('members', 'apps'),
            ),
            {
                'data': {
                    'apps': [str(app.id) for app in self.org.apps.all().order_by('created_at')],
                    'created_at': str(self.org.created_at),
                    'id': str(self.org.id),
                    'members': [str(m.id) for m in self.org.members.all()],
                    'name': self.org.name,
                    'owner': str(self.org.owner_id),
                },
            },
        )
        self.assertEqual(
            serialize(
                [self.org],
                whitelist=('members', 'owner'),
                blacklist=('apps', 'owner'),
                return_single_object=True,
                expand_fields=('members', ),
            ),
            {
                'data': {
                    'members': [str(m.id) for m in self.org.members.all()],
                },
            },
        )

    def test_serialize_aliases(self):
        self.assertEqual(
            serialize(
                [self.org],
                expand_fields=('members', 'apps'),
                alias_list={
                    'apps': 'members',
                    'owner': 'king',
                    'id': 'cenepeu',
                    'members': 'apps',
                },
            ),
            {
                'data': [
                    {
                        'members': [str(app.id) for app in self.org.apps.all().order_by('created_at')],
                        'created_at': str(self.org.created_at),
                        'cenepeu': str(self.org.id),
                        'apps': [str(m.id) for m in self.org.members.all().order_by('-created_at')],
                        'name': self.org.name,
                        'king': str(self.org.owner_id),
                    },
                ],
            },
        )
        self.assertEqual(
            serialize(
                [self.org],
                whitelist=('members', 'owner'),
                blacklist=('apps', 'owner'),
                return_single_object=True,
                expand_fields=('members', ),
                alias_list={
                    'id': 'peca',
                    'members': 'squad',
                },
            ),
            {
                'data': {
                    'squad': [str(m.id) for m in self.org.members.all().order_by('-created_at')],
                },
            },
        )
