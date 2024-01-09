import json

from ..models.generic_event import GenericEvent
from ..models.session import Session
from ..utils import JSONHttpResponse, generate_session_token
from .classes import PMTestCase


class StatsViewTestCase(PMTestCase):
    def test_post_200(self):
        session = Session(
            participant=self.participant,
            conference=self.conference,
        )
        session.save()

        token = generate_session_token(session)

        response = self.client.post(
            path='/v1/stats',
            data={
                'token': token.decode('utf-8'),
                'event': 'nume_de_event',
                'peerId': str(self.other_participant.id),
                'data': {
                    'audio': 'audio',
                    'connection': 'connection',
                    'video': 'video',
                },
            },
            content_type='application/json',
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), '')

        events_no = GenericEvent.objects.filter(
            type='stats',
            session=session,
        ).count()

        self.assertGreater(events_no, 0)
