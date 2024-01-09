import uuid

from django.core.exceptions import ValidationError

from ..errors import (APP_NOT_FOUND, PMError)
from ..models.app import App
from ..utils import JSONHttpResponse
from .generic_view import GenericView


class AppsResetApiKeyView(GenericView):
    """
    Endpoint used to reset the api key of an app.
    """

    @classmethod
    def post(cls, request, pk):
        """
        Receives an app id and resets the api_key of the app if found. Returns the new api_key.

        :param request: the received request
        :param pk: the id of the app
        """
        try:
            app = App.get(id=pk)
        except (ValidationError, App.DoesNotExist):
            raise PMError(status=400, app_error=APP_NOT_FOUND)

        app.api_key = str(uuid.uuid4()).strip('-')

        app.save()

        return JSONHttpResponse(status=200, content={'api_key': app.api_key})
