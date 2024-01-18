import json
import re
import time
import urllib.request
import jwt

from django.conf import settings
from django.db.models.fields.reverse_related import ManyToOneRel, ManyToManyRel, OneToOneRel
from django.db.models.fields.related import ManyToManyField
from django.http import HttpResponse

from .errors import INVALID_API_KEY, INVALID_META, INVALID_PARAMETERS, PMError
from .taskqueue import Taskqueue

class JSONHttpResponse(HttpResponse):
    """
    An HttpResponse wrapper used to format the response in JSON format. The default response type.
    """
    def __init__(self, content='', *args, **kwargs):
        super().__init__(content=json.dumps(content), content_type='application/json; charset=utf-8', *args, **kwargs)


def validate_string(value):
    """
    Raises an exception if the supplied object is neither None nor a string

    :param value: the object to be validated
    :return the supplied string
    :raises PMError
    """
    if value is None or isinstance(value, str):
        return value
    raise PMError(
        status=400,
        app_error=INVALID_PARAMETERS,
    )


def validate_positive_number(value):
    """
    Raises an exception if the supplied object is not a positive integer

    :param value: the object to be validated
    :return the supplied number
    :raises PMError
    """
    if (isinstance(value, float) or isinstance(value, int)) and value >= 0:
        return value
    raise PMError(
        status=400,
        app_error=INVALID_PARAMETERS,
    )


def validate_api_key(api_key):
    """
    Checks if the supplied object is a valid api_key. The requirements:
    - must be string (max 32 chars)
    - only alfanumeric chars

    :param api_key: the supplied object
    :return the input object if it's valid
    :raises PMError
    """
    if (
        isinstance(api_key, str)
        and len(api_key) == 32
        and re.match('^[a-z0-9]+$', api_key)
    ):
        return api_key
    else:
        raise PMError(
            status=400,
            app_error=INVALID_API_KEY,
        )


def is_valid_meta(meta):
    """
    Checks if the supplied object is a valid meta dict. The requirements:
    - a dict
    - no more than 5 keys
    - the keys must be strings (max 64 chars)
    - the values must be strings (max 128 chars), ints or bools

    :param meta: the supplied object
    :return True if it's valid, False otherwise
    """
    if not meta:
        return True

    if not isinstance(meta, dict):
        return False

    if len(meta.keys()) > 5:
        return False

    for key in meta.keys():
        if not isinstance(key, str) or len(key) > 64:
            return False

        if (
            not (isinstance(meta[key], str) and len(meta[key]) < 128)
            and not isinstance(meta[key], int)
            and not isinstance(meta[key], bool)
        ):
            return False

    return True


def validate_meta(meta):
    """
    Validates the supplied object, returns it or raises an exception if it's invalid.

    :param meta: the supplied object
    :return the object if it's a valid meta dict
    :raises PMError
    """
    if not is_valid_meta(meta):
        raise PMError(
            status=400,
            app_error=INVALID_META,
        )
    return meta


def serialize(
        objs, return_single_object=False, whitelist=None, blacklist=None, properties=[],
        expand_fields=None, alias_list=None, post_serialize=None,
):
    """
    Function for serializing Django models. The output format is a list of dicts containing the serialized data from the
    input objects. The output (in list form) is compliant with the JSON API. If you opt for returning a single object
    the format of the output is a single dictionary containing the data.

    :param objs: a list of objects for serializing
    :param return_single_object: a flag for returning only the first serialized object; usefull for when you want to
        serialize only a single object
    :param whitelist: if supplied only these field names will be included in the serialized objects
    :param blacklist: if supplied these fields will not be included in the serialized objects
    :param properties: a list of properties that we also want to be serialized but are not on the model's fields list. eg: session.start_time
    :param expand_fields: if supplied these fields will be included in the serialized objects (ManyToMany relationships
        and such)
    :param alias_list: a dictionary containing mappings for aliased to the proper Django field names; useful when you
        want to customize the serialized object's field names
    :param post_serialize: a method to apply for each object after being serialized
    :return a list of serialized objects or a single object if the return_single_object flag is set
    """

    if blacklist is None:
        blacklist = ('is_active', )
    else:
        blacklist += ('is_active', )

    result = {
        'data': [],
    }

    final_alias_list = {
        'pk': 'id',
    }

    expand_fields = expand_fields if expand_fields else ()
    alias_list = {} if alias_list is None else alias_list

    final_alias_list.update(alias_list)

    for obj in objs:
        d = {}
        for field in obj._meta.get_fields():
            key = field.name
            if (
                key[0] == '_'  # if the key is a private attribute
                or (whitelist and key not in whitelist)
                or (blacklist and key in blacklist)
            ):
                continue
            if isinstance(field, ManyToOneRel) or isinstance(field, ManyToManyRel):
                if key not in expand_fields:
                    continue
                value = [str(o.id) for o in field.related_model.filter(**{field.field.name: obj})]
                # OneToOneRel is a subclass of ManyToOneRel
                if isinstance(field, OneToOneRel):
                    # being a OneToOneRel we can only have one result here
                    value = value[0]
            elif isinstance(field, ManyToManyField):
                if key not in expand_fields:
                    continue
                value = [str(o.id) for o in field.related_model.filter(**{field.related_query_name(): obj})]
            else:
                # case for regular fields, ForeignKeys and OneToOneFields
                value = obj.serializable_value(key)

                # check if the object has choices available and if so return the label
                if field.choices and value:
                    value = dict(field.choices)[value]

                try:
                    json.dumps(value)  # non-JSON serializable objects must be converted to strings
                except TypeError:
                    value = str(value)

            if key in final_alias_list.keys():
                d[final_alias_list[key]] = value
            else:
                d[key] = value

        for key in properties:
            value = getattr(obj, key)

            if key in final_alias_list.keys():
                d[final_alias_list[key]] = value
            else:
                d[key] = value

        result['data'].append(d if post_serialize is None else post_serialize(d))

    if return_single_object:
        result['data'] = result['data'][0]

    return result


def serialize_one_object(obj, *args, **kwargs):
    """
    Wrapper over serialize.
    """
    return serialize([obj], return_single_object=True, *args, **kwargs)


def generate_session_token(session):
    """
    Generates a valid session token for a given session.

    :param session: the supplied Session object
    :return the token
    """
    return generate_token(
        payload={
            's': str(session.id),
            't': time.time(),
        },
        secret=settings.SESSION_TOKEN_SECRET,
    )


def generate_token(payload, secret):
    """
    Generates a jwt token.

    :param payload: the supplied payload
    :param secret: the supplied secret
    :return the jwt token
    """
    return jwt.encode(
        payload=payload,
        key=secret,
        algorithm='HS256',
    )


def get_client_ip(request):
    """
    Returns the ip address from an HTTP request.

    :param request: the supplied request
    :return the ip address from the given request
    """
    x_forwarded_for = request.headers.get('X-Forwarded-For')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.headers.get('Remote-Addr')
    return ip


def get_geoip_data(headers, ip_address):
    """
    Used to get geo ip data about an ip address. Most likely this info is available in the request headers.

    :param headers: the supplied HTTP headers
    :param ip_address: the supplied ip address
    :return the geoip data in dict format
    """
    # appengine country
    # https://cloud.google.com/appengine/docs/standard/python/reference/request-response-headers
    country = headers.get('X-AppEngine-Country', '')

    geoip_data = {
        'country_code': None,
        'region_code': None,
        'city': None,
        'latitude': None,
        'longitude': None,
    }

    if country and country != 'ZZ':
        # if we have the country header, and it's different than ZZ (unknown)
        region = headers.get('X-AppEngine-Region', '')
        city = headers.get('X-AppEngine-City', '')
        lat_long = headers.get('X-AppEngine-CityLatLong', ',')

        lat_long = lat_long.split(',')
        latitude = lat_long[0]
        longitude = lat_long[1]

        geoip_data = {
            'country_code': country,
            'region_code': region,
            'city': city,
            'latitude': latitude,
            'longitude': longitude,
        }

    # if we have an ip address, try and get geoip from a provider
    elif ip_address and settings.USE_EXTERNAL_GEOIP_PROVIDER:
        provider = settings.GEOIP_PROVIDERS[0]
        url = provider['url'].format(ip_address)

        # in case the request fails
        try:
            response_data = json.loads(urllib.request.urlopen(url).read().decode('utf-8'))

            geoip_data = {k: v for k, v in response_data.items() if k in geoip_data.keys()}
        except Exception as e:
            pass

    return geoip_data

def build_conference_summary(conference):
    """Used to start the conference summary job"""

    if not conference:
        return

    try:
        Taskqueue().create_task('summary', {'conference_id': str(conference.id)})
    except Exception as e:
        pass

def clamp(n, smallest, largest):
    return max(smallest, min(n, largest))