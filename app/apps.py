import logging
import os
import threading
import time

from django.apps import AppConfig

logger = logging.getLogger(__name__)

_cleanup_started = False
_cleanup_lock = threading.Lock()

CLEANUP_LOCK_KEY = 'conference_cleanup_lock'


class UsersConfig(AppConfig):
    name = 'app'

    def ready(self):
        global _cleanup_started

        # Each worker starts a cleanup thread, but only one acquires the Redis
        # lock per cycle. Safe across multiple gunicorn workers and multiple
        # API instances. Set ENABLE_INLINE_CONFERENCE_CLEANUP=true to enable.
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
            # Stagger startup so workers don't wake simultaneously
            time.sleep(60)

            from django.core.cache import cache

            while True:
                try:
                    # Try to acquire a distributed lock via Redis. cache.add()
                    # maps to SET NX — only one process across the entire
                    # deployment succeeds per cycle. Lock auto-expires at
                    # interval so a crashed worker doesn't block future runs.
                    lock_ttl = max(interval, 60)
                    got_lock = cache.add(CLEANUP_LOCK_KEY, os.getpid(), timeout=lock_ttl)

                    if got_lock:
                        logger.info(f'[ConferenceCleanup] Acquired lock, running cleanup (pid={os.getpid()})')
                        try:
                            from app.management.commands.cleanup_stale_conferences import Command
                            hours = int(os.getenv('CONFERENCE_TIMEOUT_HOURS', 4))
                            Command().handle(hours=hours, dry_run=False, verbosity=0)
                        finally:
                            # Release early so next cycle can run immediately
                            cache.delete(CLEANUP_LOCK_KEY)
                    else:
                        logger.debug(f'[ConferenceCleanup] Another worker holds the lock, skipping (pid={os.getpid()})')
                except Exception as e:
                    logger.warning(f'[ConferenceCleanup] Error: {e}')

                time.sleep(interval)

        thread = threading.Thread(target=cleanup_loop, daemon=True, name='conference-cleanup')
        thread.start()
