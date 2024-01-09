import json
from urllib.parse import urlparse

from django.conf import settings

from .generic_view import GenericView

from ..models.app import App
from ..models.conference import Conference
from ..models.participant import Participant

from ..decorators import check_request_body
from ..utils import (JSONHttpResponse, validate_string, validate_api_key)
from ..errors import (INVALID_API_KEY, MISSING_PARAMETERS, CONFERENCE_NOT_FOUND, PARTICIPANT_NOT_FOUND, PMError)

class GetUrlView(GenericView):
    """
    API endpoint used to return the peer metrics URL for a conference or a participant

    The user can use this to get the link and display it inside their internal tools
    """

    @classmethod
    @check_request_body
    def post(cls, request, *args, **kwargs):

        api_key = request.request_data.get('apiKey')

        conference_id = validate_string(request.request_data.get('conferenceId'))
        participant_id = validate_string(request.request_data.get('userId'))

        if not api_key and (not conference_id or not participant_id):
            raise PMError(status=400, app_error=MISSING_PARAMETERS)

        api_key = validate_api_key(api_key)

        try:
            app = App.get(api_key=api_key)
        except App.DoesNotExist:
            raise PMError(status=400, app_error=INVALID_API_KEY)

        if conference_id:
            conference_id = conference_id[:Conference._meta.get_field('conference_id').max_length]

            try:
                conference = Conference.get(conference_id=conference_id, app_id=app.id)

                # TODO: find a better way to build these urls
                return JSONHttpResponse({
                    "url": settings.LINKS['conference'] + str(conference.id)
                })
            except Exception as e:
                raise PMError(status=400, app_error=CONFERENCE_NOT_FOUND)

        elif participant_id:
            participant_id = participant_id[:Participant._meta.get_field('participant_id').max_length]

            try:
                participant = Participant.get(participant_id=participant_id, app_id=app.id)

                return JSONHttpResponse({
                    "url": settings.LINKS['participant'] + str(participant.id)
                })
            except Exception as e:
                raise PMError(status=400, app_error=PARTICIPANT_NOT_FOUND)


        raise PMError(status=400)
