# import datetime
import json

from django.conf import settings
from django.http import HttpRequest
from django.urls import resolve, reverse

from .logger import log

if settings.USE_GOOGLE_TASK_QUEUE:
    try:
        from google.cloud import tasks_v2
    except ImportError:
        log.error('Could not import google.cloud.tasks_v2')

class Taskqueue:

    _urlMap = {
        'webhook': 'job-webhook'
    }

    @staticmethod
    def _create_task_body(path, payload):
        return {
            # Specify the type of request.
            'http_request': {
                'http_method': tasks_v2.HttpMethod.POST,
                # TODO: need a better way to build absolute URL
                'url': '{}{}'.format(settings.TASK_QUEUE_DOMAIN, path),
                # The API expects a payload of type bytes.
                'body': payload,
            },
        }

    @classmethod
    def create_task(cls, task_name, body):
        url = reverse(cls._urlMap.get('webhook'))
        payload = json.dumps({
            "task": task_name,
            "payload": body
        }).encode('utf-8')

        if settings.USE_GOOGLE_TASK_QUEUE:
            client = tasks_v2.CloudTasksClient()
            parent = client.queue_path(settings.PROJECT_ID, settings.APP_LOCATION, settings.QUEUE_NAME)

            task = Taskqueue._create_task_body(url, payload)

            response = client.create_task(parent=parent, task=task)

            print('Created task {}'.format(response.name))

        else:
            request = HttpRequest()
            request.method = 'post'
            request._body = payload

            resolve(url).func(request)
