import logging
import os
import threading
import time

from django.apps import AppConfig

logger = logging.getLogger(__name__)

_cleanup_started = False
_cleanup_lock = threading.Lock()

CLEANUP_LOCK_KEY = 'conference_cleanup_lock'
CLEANUP_LOCK_TTL_SECONDS = 30 * 60


class UsersConfig(AppConfig):
    name = 'app'

    def ready(self):
        global _cleanup_started

        if os.getenv('ENABLE_INLINE_CONFERENCE_CLEANUP', '').lower() != 'true':
            return

        interval = int(os.getenv('CONFERENCE_CLEANUP_INTERVAL_SECONDS', 3600))
        if interval <= 0:
            return

        with _cleanup_lock:
            if _cleanup_started:
                return
            _cleanup_started = True

        def cleanup_loop():
            time.sleep(60)

            from django.core.cache import cache

            while True:
                try:
                    # django-redis lock: unique token per acquisition, atomic
                    # compare-and-delete on release. blocking=False skips the
                    # cycle if another worker holds the lock.
                    lock = cache.lock(
                        CLEANUP_LOCK_KEY,
                        timeout=CLEANUP_LOCK_TTL_SECONDS,
                    )

                    if lock.acquire(blocking=False):
                        logger.info(f'[ConferenceCleanup] Acquired lock, running cleanup (pid={os.getpid()})')
                        try:
                            from app.management.commands.cleanup_stale_conferences import Command
                            hours = int(os.getenv('CONFERENCE_TIMEOUT_HOURS', 4))
                            Command().handle(hours=hours, dry_run=False, verbosity=0)
                        finally:
                            try:
                                lock.release()
                            except Exception as e:
                                logger.warning(
                                    f'[ConferenceCleanup] Could not release lock, likely expired mid-run: {e}'
                                )
                    else:
                        logger.debug(f'[ConferenceCleanup] Another worker holds the lock, skipping (pid={os.getpid()})')
                except Exception as e:
                    logger.warning(f'[ConferenceCleanup] Error: {e}')

                time.sleep(interval)

        thread = threading.Thread(target=cleanup_loop, daemon=True, name='conference-cleanup')
        thread.start()
