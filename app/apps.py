import logging
import os
import threading
import time

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class UsersConfig(AppConfig):
    name = 'api'

    def ready(self):
        interval = int(os.getenv('CONFERENCE_CLEANUP_INTERVAL_SECONDS', 3600))

        if interval <= 0:
            return

        def cleanup_loop():
            # Wait before first run to let the app fully start
            time.sleep(60)

            while True:
                try:
                    from app.management.commands.cleanup_stale_conferences import Command
                    Command().handle(hours=int(os.getenv('CONFERENCE_TIMEOUT_HOURS', 4)), dry_run=False, verbosity=1)
                except Exception as e:
                    logger.warning(f'[ConferenceCleanup] Error: {e}')

                time.sleep(interval)

        thread = threading.Thread(target=cleanup_loop, daemon=True, name='conference-cleanup')
        thread.start()
