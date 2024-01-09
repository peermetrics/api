
from ..errors import MISSING_PARAMETERS, USER_NOT_OWNER, PMError
from ..utils import JSONHttpResponse, serialize
from .generic_view import GenericView


class CrudView(GenericView):
    """
    Default class for models where we want create, remove, update and delete functionalities.

    Attrs:
        model: the model we want to offer endpoints for
        user_id_filter_field: the way we acces the user field to compare if the user from the request has acces to the
            resource
        not_found_error: the not fund error specific for the model
        filter_whitelist: the whitelist to be passed to filter serialize calls
        filter_blacklist: the blacklist to be passed to filter serialize calls
        filter_expand_fields: the expand_fields to be passed to filter serialize calls
        get_whitelist: the whitelist to be passed to get serialize calls
        get_blacklist: the blacklist to be passed to get serialize calls
        get_expand_fields: the expand_fields to be passed to get serialize calls
    """
    model = None
    user_id_filter_field = None
    not_found_error = None
    filter_whitelist = None
    filter_blacklist = None
    filter_expand_fields = None
    get_whitelist = None
    get_blacklist = None
    get_expand_fields = None

    @classmethod
    def filter(cls, request):
        """
        Default filter method. Returns all the objects from the model that the user has access to.
        """

        obj = cls.model.all()

        return JSONHttpResponse(
            content=serialize(
                obj,
                blacklist=cls.filter_blacklist,
                whitelist=cls.filter_whitelist,
                expand_fields=cls.filter_expand_fields,
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
            obj = cls.model.get(id=pk)
        except cls.model.DoesNotExist:
            raise PMError(status=400, app_error=cls.not_found_error)

        return JSONHttpResponse(
            content=serialize(
                [obj],
                blacklist=cls.get_blacklist,
                whitelist=cls.get_whitelist,
                return_single_object=True,
                expand_fields=cls.get_expand_fields,
            ),
        )

    @classmethod
    def delete(cls, request, pk=None):
        """
        Default delete method. Deletes the object if the user has access to it.
        """
        if not pk:
            raise PMError(status=400, app_error=MISSING_PARAMETERS)

        try:
            cls.model.get(id=pk).soft_delete()
        except cls.model.DoesNotExist:
            raise PMError(status=400, app_error=cls.not_found_error)

        return JSONHttpResponse(status=200)
