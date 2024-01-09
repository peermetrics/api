import json

from ..decorators import check_request_body
from ..errors import (MAX_ORGANIZATIONS_REACHED, METHOD_NOT_ALLOWED, MISSING_PARAMETERS,
                      ORGANIZATION_NOT_FOUND, PMError)
from ..models.organization import Organization
from ..utils import JSONHttpResponse, serialize, validate_string
from .crud_view import CrudView

class OrganizatonsView(CrudView):
    """
    Endpoint for editing, creating and retrieving organizations.
    """
    model = Organization
    user_id_filter_field = 'members__id'
    not_found_error = ORGANIZATION_NOT_FOUND

    @classmethod
    @check_request_body
    def post(cls, request, pk=None):
        """
        Method for creating a new organization.

        :param request: the received request
        :param pk: the id of the resource, should not be supplied
        """
        if pk:
            raise PMError(status=405, app_error=METHOD_NOT_ALLOWED)

        organization_name = validate_string(request.request_data.get('name'))

        if not organization_name:
            raise PMError(status=400, app_error=MISSING_PARAMETERS)

        if Organization.objects.count():
            raise PMError(status=400, app_error=MAX_ORGANIZATIONS_REACHED)

        organization = cls.model()

        organization.name = organization_name[:Organization._meta.get_field('name').max_length]

        organization.save()

        return JSONHttpResponse(
            status=200,
            content=serialize(
                [organization],
                return_single_object=True,
            ),
        )

    @classmethod
    @check_request_body
    def put(cls, request, pk):
        """
        Method for updating an existing organization.

        :param request: the received request
        :param pk: the id of the resource
        """
        try:
            organization = cls.model.get(id=pk)
        except Organization.DoesNotExist:
            raise PMError(status=400, app_error=ORGANIZATION_NOT_FOUND)

        attr_white_list = [
            'name',
        ]

        values = [
            (white_attr, request.request_data.get(white_attr))
            for white_attr in attr_white_list
        ]

        organization.set_values(values)
        organization.save()

        return JSONHttpResponse(
            status=200,
            content=serialize(
                [organization],
                return_single_object=True,
            ),
        )
