import datetime

from django.core.management.base import BaseCommand
from django.db.models import Max

from app.models.conference import Conference
from app.models.generic_event import GenericEvent


class Command(BaseCommand):
    help = 'Close conferences with no activity for longer than the specified hours'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=4,
            help='Close conferences with no activity for this many hours (default: 4)',
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

        ongoing = Conference.objects.filter(ongoing=True)

        if not ongoing.exists():
            self.stdout.write('No ongoing conferences found.')
            return

        stale = []
        for conference in ongoing:
            last_event = GenericEvent.objects.filter(
                conference=conference
            ).aggregate(last=Max('created_at'))['last']

            last_activity = last_event or conference.created_at

            if last_activity < cutoff:
                idle = now - last_activity
                stale.append((conference, last_activity, idle))

        if not stale:
            self.stdout.write(f'{ongoing.count()} ongoing conferences found, all have recent activity.')
            return

        self.stdout.write(f'Found {len(stale)} conferences with no activity for more than {hours} hours.')

        for conference, last_activity, idle in stale:
            self.stdout.write(f'  {conference.id} ({conference.conference_name or conference.conference_id}) - last activity {idle} ago')

            if not dry_run:
                for connection in conference.connections.filter(end_time__isnull=True):
                    connection.end(now)
                    connection.save()

                for session in conference.sessions.filter(end_time__isnull=True):
                    session.should_stop_call(now)
                    session.save()

                conference.should_stop_call(now)
                conference.save()

        if dry_run:
            self.stdout.write(f'\nDry run - no changes made. Run without --dry-run to close these conferences.')
        else:
            self.stdout.write(f'\nClosed {len(stale)} stale conferences.')
