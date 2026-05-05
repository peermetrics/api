"""
Smoke tests for prewarm_summaries management command (PR #28).
"""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from app.models.app import App
from app.models.conference import Conference
from app.models.organization import Organization


class PrewarmSummariesSmokeTests(TestCase):
    def test_runs_with_no_qualifying_apps(self):
        out = StringIO()
        err = StringIO()
        call_command('prewarm_summaries', stdout=out, stderr=err)

        combined = out.getvalue() + err.getvalue()
        self.assertIn('Warming 0 active apps', combined)
        self.assertIn('Warmed 0 summary entries across 0 apps', combined)

    def test_runs_for_one_app_with_recent_conference(self):
        org = Organization.objects.create(name='Prewarm Org')
        app = App.objects.create(
            name='Prewarm App',
            api_key='b' * 32,
            organization=org,
        )
        Conference.objects.create(
            conference_id='prewarm-conf-1',
            app=app,
        )

        out = StringIO()
        call_command('prewarm_summaries', stdout=out, stderr=StringIO())
        text = out.getvalue()

        self.assertIn('Warming 1 active apps', text)
        self.assertIn('Warmed 8 summary entries across 1 apps', text)
