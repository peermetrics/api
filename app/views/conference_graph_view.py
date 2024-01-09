import datetime

from .event_view import EventView
from .generic_view import GenericView

from ..models.conference import Conference
from ..models.summary import SUMMARY_STATUS_ENUM, CURRENT_SUMMARY_VERSION

from ..errors import METHOD_NOT_ALLOWED, CONFERENCE_NOT_FOUND, PMError
from ..utils import JSONHttpResponse, serialize, build_conference_summary

from ..logger import log

class ConferenceGraphView(GenericView):

    @classmethod
    def get(cls, request, pk=None):
        if not pk:
            raise PMError(status=405, app_error=METHOD_NOT_ALLOWED)

        try:
            conference = Conference.get(id=pk)
        except Conference.DoesNotExist:
            raise PMError(status=400, app_error=CONFERENCE_NOT_FOUND)

        response = {}
        if conference.ongoing:
            response['ongoing'] = True
        else:
            if hasattr(conference, 'summary'):
                if conference.summary.status == SUMMARY_STATUS_ENUM['ongoing']:
                    response['building'] = True

                # if we have a new version of a summary, rebuild it
                elif conference.summary.version != CURRENT_SUMMARY_VERSION:
                    log.warning('Rebuilding the summary as the version changed. Conference: {}'.format(conference.id))
                    # delete the old one
                    build_conference_summary(conference)
                    response['building'] = True

                elif conference.summary.status == SUMMARY_STATUS_ENUM['done']:
                    response['summary'] = serialize([conference.summary], whitelist=['data'], return_single_object=True)['data']

                else:
                    log.warning('Building the summary again. Conference: {}'.format(conference.id))
                    build_conference_summary(conference)
                    response['building'] = True

            else:
                # start building it
                log.warning('Did not have a summary when user requested it. Conference: {}'.format(conference.id))
                build_conference_summary(conference)
                response['building'] = True

        return JSONHttpResponse(content=response)
