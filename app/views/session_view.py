import datetime

from django.core.exceptions import ValidationError

from ..decorators import (check_authorization, check_initial_authorization, check_request_body)
from ..errors import (APP_NOT_FOUND, CONFERENCE_NOT_FOUND, METHOD_NOT_ALLOWED,
                      MISSING_PARAMETERS, PARTICIPANT_NOT_FOUND, PMError)
from ..models.app import App
from ..models.issue import Issue
from ..models.conference import Conference
from ..models.participant import Participant
from ..models.session import Session
from ..utils import (JSONHttpResponse, generate_session_token, get_client_ip, get_geoip_data,
                     serialize, validate_string, validate_meta, validate_positive_number)
from .generic_view import GenericView


class SessionView(GenericView):
    """
    View for handling the session model.
    """

    @classmethod
    def get(cls, request):
        """
        Receives an HTTP request containing several possible get parameters (and the response varies depending on them):
            conferenceId: returns all the sessions of a given conference
            participantId: returns all the sessions in which a given participant is involved
            appId: returns all the sessions of a given app

        :param request: the HTTP request
        """

        try:
            conference = Conference.get(
                id=request.GET.get('conferenceId'),
            ) if request.GET.get('conferenceId') else None
        except (ValidationError, Conference.DoesNotExist):
            raise PMError(status=400, app_error=CONFERENCE_NOT_FOUND)
        try:
            participant = Participant.get(
                id=request.GET.get('participantId'),
            ) if request.GET.get('participantId') else None
        except (ValidationError, Participant.DoesNotExist):
            raise PMError(status=400, app_error=PARTICIPANT_NOT_FOUND)
        try:
            app = App.get(
                id=request.GET.get('appId'),
            ) if request.GET.get('appId') else None
        except (ValidationError, App.DoesNotExist):
            raise PMError(status=400, app_error=APP_NOT_FOUND)

        objs = None
        max_days = 30

        if conference or participant:

            filters = {
                'created_at__gt': datetime.datetime.utcnow() - datetime.timedelta(days=max_days),
            }
            if conference:
                filters['conference'] = conference

            if participant:
                filters['participant'] = participant

            objs = Session.filter(**filters)

        elif app:
            objs = Session.filter(
                conference__id__in=Conference.filter(app=app).values_list('id', flat=True),
                created_at__gt=datetime.datetime.utcnow() - datetime.timedelta(days=max_days),
            )

        if objs is not None:
            return JSONHttpResponse(
                status=200,
                content=serialize(
                    objs,
                    blacklist=('billing_start', 'billed_time', 'constraints'),
                    expand_fields=('issues', ),
                )
            )

        raise PMError(status=400, app_error=MISSING_PARAMETERS)

    @classmethod
    @check_request_body
    @check_initial_authorization
    def post(cls, request, pk=None):
        """
        Receives an HTTP request and uses the data within to create a session object. Needs a token generated in the
        InitializeView. Generates and returns a session token used for authentication in many other views.

        :param request: the HTTP request
        :param pk: if this path variable is supplied raises an HTTP 405 error
        """
        if pk:
            raise PMError(status=405, app_error=METHOD_NOT_ALLOWED)

        app_version = validate_string(request.request_data.get('appVersion'))
        webrtc_sdk = validate_string(request.request_data.get('webrtcSdk'))

        session = Session()

        session.participant = request.participant
        session.conference = request.conference

        session.metadata = validate_meta(request.request_data.get('meta'))
        session.constraints = request.request_data.get('constraints')
        session.devices = request.request_data.get('devices')
        session.platform = request.request_data.get('platform')

        if app_version:
            session.app_version = app_version[:Session._meta.get_field('app_version').max_length]

        if webrtc_sdk:
            session.webrtc_sdk = webrtc_sdk[:Session._meta.get_field('webrtc_sdk').max_length]

        delta = validate_positive_number(request.request_data.get('delta', 0))
        session.created_at = datetime.datetime.utcnow() - datetime.timedelta(milliseconds=delta)

        session.geo_ip = get_geoip_data(
            headers=request.headers,
            ip_address=get_client_ip(request),
        )

        session.save()

        # check to see if we have multiple sessions for this user
        count = Session.objects.filter(participant=request.participant, conference=request.conference).count()
        if count > 1:
            Issue(
                code='multiple_rejoins',
                type=Issue.TYPES_OF_ISSUES['warning'],
                participant=request.participant,
                session=session,
                conference=request.conference
            ).save()

        token = generate_session_token(session)

        response = {
            'token': token.decode('utf-8'),
        }
        return JSONHttpResponse(status=200, content=response)

    @classmethod
    @check_request_body
    @check_authorization
    def put(cls, request):
        """
        Receives an HTTP request and updates the session from the token. It updates only the fields found in
        attr_white_list (if supplied).

        :param request: the HTTP request
        """

        attr_white_list = [
            'constraints',
            'devices',
            'platform',
        ]

        values = [(white_attr, request.request_data.get(white_attr)) for white_attr in attr_white_list]

        request.peer_session.set_values(values)

        # can't use attr_white_list for this one, different name
        request.peer_session.webrtc_sdk = validate_string(request.request_data.get('webrtcSdk'))
        request.peer_session.save()

        return JSONHttpResponse(
            status=200,
            content=serialize(
                [request.peer_session],
                return_single_object=True,
            ),
        )
