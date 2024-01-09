import datetime

from django.db import transaction

from .generic_view import GenericView

from ..models.app import App
from ..models.conference import Conference

from ..decorators import check_request_body
from ..utils import (JSONHttpResponse, validate_string, validate_api_key)
from ..errors import (INVALID_API_KEY, MISSING_PARAMETERS, CONFERENCE_NOT_FOUND, PMError)

class StopConferenceView(GenericView):
    """
        Used to force stop a conference.

        This is usually called from the user's server
    """

    @classmethod
    @check_request_body
    def post(self, request, *args, **kwargs):

        api_key = request.request_data.get('apiKey')
        conference_id = validate_string(request.request_data.get('conferenceId'))

        if not api_key or not conference_id:
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

                now = datetime.datetime.now()

                with transaction.atomic():
                    # end all the connections
                    for connection in conference.connections.all():
                        connection.end(now)
                        connection.save()

                    # end all the sessions
                    for session in conference.sessions.all():
                        session.should_stop_call(now)
                        session.save()

                    # stop the conference
                    conference.should_stop_call(now)
                    conference.save()

                return JSONHttpResponse({})

            except Conference.DoesNotExist:
                raise PMError(status=400, app_error=CONFERENCE_NOT_FOUND)

            except Exception as e:
                self.log.warning(e)
                raise PMError(status=400, app_error=CONFERENCE_NOT_FOUND)

        raise PMError(status=400)
