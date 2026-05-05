"""
Pre-warm the dashboard-summary Redis cache so first visitors don't pay
the cold-query tax. Intended to run every ~30s via ECS scheduled task.

For each active app that has seen recent data, walks every summary view
with the same (appId, created_at_gte) filter the dashboard sends by
default (last 30 days). The views themselves populate the cache on miss.
"""
import datetime
import logging
import time

from django.core.management.base import BaseCommand
from django.test.client import RequestFactory

from app.models.app import App
from app.models.conference import Conference

from app.views.conference_summary_view import ConferenceSummaryView
from app.views.conference_duration_summary_view import ConferenceDurationSummaryView
from app.views.conference_participant_count_summary_view import ConferenceParticipantCountSummaryView
from app.views.issue_summary_view import IssueSummaryView, GetUserMediaSummaryView
from app.views.connection_summary_view import ConnectionSummaryView, ConnectionSetupTimeSummaryView
from app.views.session_summary_view import SessionSummaryView

logger = logging.getLogger(__name__)

# (label, view)
VIEWS = [
    ('conferences.summary',                  ConferenceSummaryView),
    ('conferences.duration_summary',         ConferenceDurationSummaryView),
    ('conferences.participant_count_summary', ConferenceParticipantCountSummaryView),
    ('issues.summary',                       IssueSummaryView),
    ('issues.gum_summary',                   GetUserMediaSummaryView),
    ('connections.summary',                  ConnectionSummaryView),
    ('connections.setup_time_summary',       ConnectionSetupTimeSummaryView),
    ('sessions.summary',                     SessionSummaryView),
]


class Command(BaseCommand):
    help = 'Pre-compute dashboard summary responses and cache them'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Window to warm (default: 30 days, matches dashboard default)',
        )
        parser.add_argument(
            '--active-within-days',
            type=int,
            default=2,
            help='Only warm apps that saw a conference in the last N days (default: 2)',
        )

    def handle(self, *args, **options):
        window_days = options['days']
        active_within = options['active_within_days']

        since_window = datetime.datetime.utcnow() - datetime.timedelta(days=window_days)
        active_since = datetime.datetime.utcnow() - datetime.timedelta(days=active_within)

        # Apps with any conference in the recent window — skip tenants with
        # no traffic so warming doesn't scan their cold tables.
        recent_app_ids = (Conference.objects
            .filter(created_at__gte=active_since)
            .values_list('app_id', flat=True)
            .distinct())
        apps = App.objects.filter(id__in=list(recent_app_ids), is_active=True)
        count = apps.count()
        self.stdout.write(f'Warming {count} active apps ({window_days}d window)')

        rf = RequestFactory()
        created_at_gte = since_window.isoformat() + 'Z'
        warmed = 0
        failed = 0

        for app in apps:
            for label, view_cls in VIEWS:
                req = rf.get('/v1/' + label, {
                    'appId': str(app.id),
                    'created_at_gte': created_at_gte,
                })
                started = time.monotonic()
                try:
                    view_cls.get(req)
                    warmed += 1
                except Exception as e:
                    failed += 1
                    logger.warning('prewarm %s for app %s failed: %s', label, app.id, e)
                elapsed_ms = (time.monotonic() - started) * 1000
                if elapsed_ms > 500:
                    self.stdout.write(f'  slow: {label} app={app.id} {elapsed_ms:.0f}ms')

        self.stdout.write(f'Warmed {warmed} summary entries across {count} apps' +
                          (f' ({failed} failed)' if failed else ''))
