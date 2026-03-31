import logging
import os
import threading
import time

from django.apps import AppConfig

logger = logging.getLogger(__name__)

_cleanup_started = False
_cleanup_lock = threading.Lock()


class UsersConfig(AppConfig):
    name = 'app'

    def ready(self):
        global _cleanup_started

        interval = int(os.getenv('CONFERENCE_CLEANUP_INTERVAL_SECONDS', 3600))
        if interval <= 0:
            return

        with _cleanup_lock:
            if _cleanup_started:
                return
            _cleanup_started = True

        def cleanup_loop():
            time.sleep(60)

            while True:
                try:
                    from app.management.commands.cleanup_stale_conferences import Command
                    hours = int(os.getenv('CONFERENCE_TIMEOUT_HOURS', 4))
                    Command().handle(hours=hours, dry_run=False, verbosity=0)
                except Exception as e:
                    logger.warning(f'[ConferenceCleanup] Error: {e}')

                time.sleep(interval)

        thread = threading.Thread(target=cleanup_loop, daemon=True, name='conference-cleanup')
        thread.start()
