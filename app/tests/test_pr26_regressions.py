import json

from django.test import Client, TestCase

from app.models.app import App
from app.models.conference import Conference
from app.models.issue import Issue
from app.models.organization import Organization
from app.models.participant import Participant
from app.models.session import Session


class PR26RegressionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.organization = Organization.objects.create(name="Test Org")
        self.app = App.objects.create(
            name="Test App",
            api_key="a" * 32,
            organization=self.organization,
        )

    def _make_conference_graph(self, conference_id):
        conference = Conference.objects.create(
            conference_id=conference_id,
            app=self.app,
        )
        participant = Participant.objects.create(
            participant_id=f"{conference_id}-participant",
            app=self.app,
        )
        participant.conferences.add(conference)
        session = Session.objects.create(
            conference=conference,
            participant=participant,
        )
        return conference, participant, session

    def test_conferences_issue_code_filter_returns_distinct_conferences(self):
        conference, participant, session = self._make_conference_graph("conf-1")

        Issue.objects.create(
            session=session,
            conference=conference,
            participant=participant,
            type=Issue.TYPES_OF_ISSUES["warning"],
            code="getusermedia_error",
            data={"name": "NotFoundError"},
        )
        Issue.objects.create(
            session=session,
            conference=conference,
            participant=participant,
            type=Issue.TYPES_OF_ISSUES["warning"],
            code="getusermedia_error",
            data={"name": "NotFoundError"},
        )

        response = self.client.get(
            "/v1/conferences",
            {
                "appId": str(self.app.id),
                "issue_code": "getusermedia_error",
                "limit": "50",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(payload["count"], 1)
        self.assertEqual(len(payload["results"]), 1)
        self.assertEqual(payload["results"][0]["id"], str(conference.id))

    def test_conferences_issue_code_filter_ignores_inactive_issues(self):
        conference_active, participant_active, session_active = self._make_conference_graph("conf-active")
        conference_inactive, participant_inactive, session_inactive = self._make_conference_graph("conf-inactive")

        Issue.objects.create(
            session=session_active,
            conference=conference_active,
            participant=participant_active,
            type=Issue.TYPES_OF_ISSUES["warning"],
            code="getusermedia_error",
            data={"name": "NotFoundError"},
            is_active=True,
        )
        Issue.objects.create(
            session=session_inactive,
            conference=conference_inactive,
            participant=participant_inactive,
            type=Issue.TYPES_OF_ISSUES["warning"],
            code="getusermedia_error",
            data={"name": "NotReadableError"},
            is_active=False,
        )

        response = self.client.get(
            "/v1/conferences",
            {
                "appId": str(self.app.id),
                "issue_code": "getusermedia_error",
                "limit": "50",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        returned_ids = {row["id"] for row in payload["results"]}
        self.assertEqual(returned_ids, {str(conference_active.id)})
        self.assertEqual(payload["count"], 1)

    def test_gum_summary_skips_non_dict_issue_data(self):
        conference, participant, session = self._make_conference_graph("conf-gum")

        Issue.objects.create(
            session=session,
            conference=conference,
            participant=participant,
            type=Issue.TYPES_OF_ISSUES["warning"],
            code="getusermedia_error",
            data={"name": "NotAllowedError", "message": "Permission denied"},
        )
        Issue.objects.create(
            session=session,
            conference=conference,
            participant=participant,
            type=Issue.TYPES_OF_ISSUES["warning"],
            code="getusermedia_error",
            data="malformed",
        )

        response = self.client.get(
            "/v1/issues/gum-summary",
            {
                "appId": str(self.app.id),
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["data"][0]["name"], "NotAllowedError")
        self.assertEqual(payload["data"][0]["count"], 1)

    def test_conferences_participant_id_filter_preserves_full_participants_count(self):
        """Count must not collapse to 1 when the list is filtered to one participant."""
        conference = Conference.objects.create(
            conference_id="conf-multi",
            app=self.app,
        )
        participants = []
        for i in range(3):
            p = Participant.objects.create(
                participant_id=f"user-{i}",
                app=self.app,
            )
            p.conferences.add(conference)
            Session.objects.create(
                conference=conference,
                participant=p,
            )
            participants.append(p)

        response = self.client.get(
            "/v1/conferences",
            {
                "appId": str(self.app.id),
                "participantId": str(participants[0].id),
                "limit": "50",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(payload["count"], 1)
        self.assertEqual(len(payload["results"]), 1)
        self.assertEqual(payload["results"][0]["id"], str(conference.id))
        self.assertEqual(payload["results"][0]["participants_count"], 3)
