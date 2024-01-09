import datetime

from ..errors import METHOD_NOT_ALLOWED, CONFERENCE_NOT_FOUND, PMError
from .generic_view import GenericView
from ..models.conference import Conference
from .event_view import EventView

class ConferenceEventsView(GenericView):

    @classmethod
    def get(cls, request, pk=None):
        if not pk:
            raise PMError(status=405, app_error=METHOD_NOT_ALLOWED)

        try:
            conference = Conference.get(id=pk)
        except Conference.DoesNotExist:
            raise PMError(status=400, app_error=CONFERENCE_NOT_FOUND)

        return EventView.retrieve_events(event_type=request.GET.get('type'), conference=conference)
