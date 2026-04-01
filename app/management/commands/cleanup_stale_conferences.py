import datetime
import os

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max, Subquery, OuterRef

from app.models.conference import Conference
from app.models.generic_event import GenericEvent


DEFAULT_TIMEOUT_HOURS = 4


class Command(BaseCommand):
    help = 'Close conferences with no activity for longer than the specified hours'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=int(os.getenv('CONFERENCE_TIMEOUT_HOURS', DEFAULT_TIMEOUT_HOURS)),
            help=f'Close conferences with no activity for this many hours (default: {DEFAULT_TIMEOUT_HOURS}, env: CONFERENCE_TIMEOUT_HOURS)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be closed without making changes',
        )

    def handle(self, *args, **options):
        hours = options['hours']
        dry_run = options['dry_run']
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
        now = datetime.datetime.utcnow()

        # Single annotated query to get last activity per conference (avoids N+1)
        ongoing = Conference.objects.filter(ongoing=True).annotate(
            last_event_at=Subquery(
                GenericEvent.objects.filter(conference=OuterRef('pk'))
                .order_by('-created_at')
                .values('created_at')[:1]
            ),
            last_connection_at=Max('connections__created_at'),
        )

        if not ongoing.exists():
            self.stdout.write('No ongoing conferences found.')
            return

        stale = []
        for conference in ongoing:
            last_activity = conference.last_event_at or conference.last_connection_at or conference.created_at

            if last_activity < cutoff:
                idle = now - last_activity
                stale.append((conference, last_activity, idle))

        if not stale:
            self.stdout.write(f'{ongoing.count()} ongoing conferences found, all have recent activity.')
            return

        self.stdout.write(f'Found {len(stale)} conferences with no activity for more than {hours} hours.')

        closed = 0
        failed = 0

        for conference, last_activity, idle in stale:
            self.stdout.write(f'  {conference.id} ({conference.conference_name or conference.conference_id}) - last activity {idle} ago')

            if not dry_run:
                try:
                    with transaction.atomic():
                        for connection in conference.connections.filter(end_time__isnull=True):
                            connection.end(now)
                            connection.save()

                        for session in conference.sessions.filter(end_time__isnull=True):
                            session.should_stop_call(now)
                            session.save()

                        conference.should_stop_call(now)
                        conference.save()

                    closed += 1
                except Exception as e:
                    failed += 1
                    self.stderr.write(f'    Error closing {conference.id}: {e}')

        if dry_run:
            self.stdout.write(f'\nDry run - no changes made. Run without --dry-run to close these conferences.')
        else:
            self.stdout.write(f'\nClosed {closed} stale conferences.' + (f' {failed} failed.' if failed else ''))
