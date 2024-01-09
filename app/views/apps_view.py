import uuid

from django.core.exceptions import ValidationError

from ..decorators import check_request_body
from ..errors import APP_NOT_FOUND, METHOD_NOT_ALLOWED, MAX_APPS_REACHED, ORGANIZATION_NOT_FOUND, MISSING_PARAMETERS, PMError
from ..models.app import App
from ..models.organization import Organization
from ..utils import JSONHttpResponse, serialize
from .crud_view import CrudView


class AppsView(CrudView):
    """
    Endpoint for editing, creating and retrieving apps.
    """

    model = App

    @classmethod
    def filter(cls, request):
        """
        Default filter method. Returns all the objects from the model that the user has access to.
        """
        app = App.objects.all()

        return JSONHttpResponse(
            content=serialize(
                app,
                post_serialize=App.get_serialize_fix_duration_days_method(),
            ),
        )

    @classmethod
    def get(cls, request, pk=None):
        """
        Default get method. Returns the object if the user has access to it. Calls filter if no id is supplied.
        """
        if not pk:
            return cls.filter(request)

        try:
            app = App.get(id=pk)
        except App.DoesNotExist:
            raise PMError(status=400, app_error=APP_NOT_FOUND)

        return JSONHttpResponse(
            content=serialize(
                [app],
                return_single_object=True,
                post_serialize=App.get_serialize_fix_duration_days_method(),
            ),
        )

    @classmethod
    @check_request_body
    def post(cls, request, pk=None):
        """
        Method for creating a new app.

        :param request: the received request
        :param pk: the id of the resource, should not be supplied
        """
        if pk:
            raise PMError(status=405, app_error=METHOD_NOT_ALLOWED)

        try:
            organization = Organization.get(id=request.request_data.get('organization'))
        except (Organization.DoesNotExist, ValidationError):
            raise PMError(status=400, app_error=ORGANIZATION_NOT_FOUND)

        app_name = request.request_data.get('name')

        if not app_name:
            raise PMError(status=400, app_error=MISSING_PARAMETERS)

        app = App()

        app.organization = organization
        app.api_key = str(uuid.uuid4()).replace('-', '')
        app.name = app_name[:App._meta.get_field('name').max_length]

        app.save()

        return JSONHttpResponse(status=200, content=serialize(
            [app],
            return_single_object=True,
            post_serialize=App.get_serialize_fix_duration_days_method(),
        ))

    @classmethod
    @check_request_body
    def put(cls, request, pk):
        """
        Method for updating an existing app.

        :param request: the received request
        :param pk: the id of the resource
        """

        try:
            app = App.get(id=pk)
        except App.DoesNotExist:
            raise PMError(status=400, app_error=APP_NOT_FOUND)

        app_name = request.request_data.get('name', '')[:App._meta.get_field('name').max_length]
        if app_name:
            app.name = app_name

        app_domain = request.request_data.get('domain', '')[:App._meta.get_field('domain').max_length]
        if app_domain:
            app.domain = app_domain

        attr_white_list = [
            'interval',
            'recording',
        ]

        values = [(white_attr, request.request_data.get(white_attr)) for white_attr in attr_white_list]

        app.set_values(values)
        app.save()

        return JSONHttpResponse(status=200, content=serialize(
            [app],
            return_single_object=True,
            post_serialize=App.get_serialize_fix_duration_days_method(),
        ))
