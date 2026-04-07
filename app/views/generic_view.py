from django.views import View
from ratelimit.mixins import RatelimitMixin
from ratelimit import ALL

from ..errors import PMError, METHOD_NOT_ALLOWED
from ..logger import log


def get_real_ip(group, request):
    return (
        request.META.get('HTTP_X_REAL_IP')
        or request.META.get('REMOTE_ADDR', '')
    ).strip()


class Logger(object):
    """
    Special logger that is tied to a specific request
    """

    def warning(self, text, labels=None, meta=None):
        log.warning(text, extra={'json_fields': meta, 'labels': labels})

    def info(self, text, labels=None, meta=None):
        log.info(text, extra={'json_fields': meta, 'labels': labels})

class GenericView(RatelimitMixin, View):
    ratelimit_group = 'api'
    ratelimit_key = get_real_ip
    ratelimit_rate = '2000/m'
    ratelimit_block = True
    ratelimit_method = ALL
    log = Logger()

    @classmethod
    def get(cls, request, *args, **kwargs):
        raise PMError(status=405, app_error=METHOD_NOT_ALLOWED)

    @classmethod
    def post(cls, request, *args, **kwargs):
        raise PMError(status=405, app_error=METHOD_NOT_ALLOWED)

    @classmethod
    def put(cls, request, *args, **kwargs):
        raise PMError(status=405, app_error=METHOD_NOT_ALLOWED)

    @classmethod
    def delete(cls, request, *args, **kwargs):
        raise PMError(status=405, app_error=METHOD_NOT_ALLOWED)
