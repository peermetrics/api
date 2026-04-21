import os
import multiprocessing

workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
threads = 2
worker_class = 'gthread'
timeout = 30
graceful_timeout = 30
# Must exceed nginx upstream `keepalive_timeout` (60s) so nginx closes first
# and we avoid races where gunicorn kills a socket nginx is about to reuse.
keepalive = 75
bind = '0.0.0.0:8081'

preload_app = True

max_requests = 1000
max_requests_jitter = 50

accesslog = '-'
errorlog = '-'

worker_tmp_dir = '/dev/shm'
