import os
import multiprocessing

workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
threads = 2
worker_class = 'gthread'
timeout = 30
bind = '0.0.0.0:8081'
