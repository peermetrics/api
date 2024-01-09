import json
import time
from urllib.parse import urlparse

from django.conf import settings

from ..errors import (APP_NOT_RECORDING, DOMAIN_NOT_ALLOWED, INVALID_API_KEY,
                      MISSING_PARAMETERS, QUOTA_EXCEEDED, PMError)
from ..models.app import App
from ..models.conference import Conference
from ..models.participant import Participant
from ..utils import (JSONHttpResponse, generate_token,
                     validate_string, validate_api_key)
from ..decorators import check_request_body
from .generic_view import GenericView


class InitializeView(GenericView):
    """
    API endpoint used at the beginning of the event collecting process.
    It checks if the apiKey is valid and if the collecting process should begin. It is the only entry point in the whole
    server that doesn't require authentication.

    This endpoint:
    - returns a token to be used with future requests (for auth)
    - returns the stats interval for this app
    - returns a timestamp to be used as base time
    """

    @classmethod
    @check_request_body
    def post(cls, request, *args, **kwargs):
        """
        Receives an HTTP request with the information needed to begin the event collecting process. It extracts the
        following data from the request:
            conferenceId: the conferenceId set by the user
            conferenceName: the conferenceName set by the user (optional)
            userId: the participantId set by the user
            userName: the participantName set by the user (optional)
            apiKey: the apiKey set by the user

        If the conferenceName and userName parameters are missing then it uses the old names for the (possibly) existing
        Conference and Participant objects.

        If the participant fails to be saved in the database then its conference is deleted.

        This endpoint responds with a token used for authentication on the SessionView view.

        :param request: the HTTP request
        """
        conference_id = validate_string(request.request_data.get('conferenceId'))
        conference_name = validate_string(request.request_data.get('conferenceName'))

        participant_id = validate_string(request.request_data.get('userId'))
        participant_name = validate_string(request.request_data.get('userName'))

        api_key = request.request_data.get('apiKey')

        if not conference_id or not participant_id or not api_key:
            raise PMError(status=400, app_error=MISSING_PARAMETERS)

        api_key = validate_api_key(api_key)

        try:
            app = App.get(api_key=api_key)
        except App.DoesNotExist:
            raise PMError(status=400, app_error=INVALID_API_KEY)

        if not app.recording:
            raise PMError(status=400, app_error=APP_NOT_RECORDING)

        origin = request.META.get('HTTP_ORIGIN')

        if app.domain:
            if origin:
                netloc = urlparse(origin).netloc
                # in case we have port in the domain
                domain = netloc.split(":")[0]
                if domain != app.domain:
                    raise PMError(status=403, app_error=DOMAIN_NOT_ALLOWED)
            else:
                raise PMError(status=403, app_error=DOMAIN_NOT_ALLOWED)

        conference_id = conference_id[:Conference._meta.get_field('conference_id').max_length]
        conference, conference_created = Conference.get_or_create(conference_id=conference_id, app_id=app.id)

        if conference_name:
            conference.conference_name = conference_name[:Conference._meta.get_field('conference_name').max_length]

        try:
            participant_id = participant_id[:Participant._meta.get_field('participant_id').max_length]
            participant, _ = Participant.get_or_create(participant_id=participant_id, app_id=app.id)

            if participant_name:
                participant.participant_name = participant_name[:Participant._meta.get_field('participant_name').max_length]

            participant.conferences.add(conference)

            participant.save()
        except PMError as exc:
            # delete the conference if the participant's save failed
            if conference_created:
                conference.delete()
            raise exc
        else:
            conference.save()

        payload = {
            'p': str(participant.id),
            'c': str(conference.id),
            't': time.time(),
        }

        token = generate_token(payload=payload, secret=settings.INIT_TOKEN_SECRET)

        response = {
            'token': token.decode('utf-8'),
            'getStatsInterval': settings.DEFAULT_INTERVAL,
            'batchConnectionEvents': settings.BATCH_CONNECTION_REQUESTS,
            'time': time.time(),
        }

        return JSONHttpResponse(response)
