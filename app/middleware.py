from .errors import PMError
from .logger import log
from .utils import JSONHttpResponse

from ratelimit.exceptions import Ratelimited


class MyExceptionMiddleware(object):
    """
    Middleware used to transform all the exceptions raised by the server into HttpResponses with specific statuses and
    content. If an exception of type PMError is raised then it may result in a response with a status code of 4xx as
    opposed to Django's default handling of exceptions (500 status code responses). This also allows for responding to
    a request by raising an exception which is more versatile than only being able to return the response as it can be
    used in called methods as well.

    The format of this class is in the standard Django middleware format.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exc):
        if isinstance(exc, PMError):
            try:
                log.warning(exc.app_error['error_code'])
                log.info(request.request_data)
            except Exception as e:
                pass

            return JSONHttpResponse(
                status=exc.status,
                content=exc.app_error,
            )

        if isinstance(exc, Ratelimited):
            log.warning(exc)
            return JSONHttpResponse(status=429)

        log.exception(exc)

        return JSONHttpResponse(status=500)
