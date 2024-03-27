import math

from datetime import datetime

from django.views import View
from django.conf import settings
from django.db import connection

from ..errors import (INVALID_PARAMETERS, CONFERENCE_NOT_FOUND,
                      MISSING_PARAMETERS, PMError)

# from .generic_view import GenericView
from .event_view import EventView

from ..models.summary import Summary, CURRENT_SUMMARY_VERSION, SUMMARY_STATUS_ENUM
from ..models.conference import Conference
from ..models.participant import Participant
from ..models.session import Session
from ..models.issue import Issue

from ..decorators import check_request_body
from ..utils import JSONHttpResponse, clamp
from ..logger import log

def dictfetchall(cursor):
    """Return all rows from a cursor as a dict"""

    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

# mapping between stats type and direction. we need for tracks
keys = {
    'inbound-rtp': 'inbound',
    'outbound-rtp': 'outbound'
}

# could not use GenericView. problem with rate limit: KeyError: 'REMOTE_ADDR'
# class JobWebhookView(GenericView):

class JobWebhookView(View):

    @check_request_body
    def post(self, request):
        log.info('job webhook data: {}'.format(request.request_data))

        task = request.request_data.get('task')
        payload = request.request_data.get('payload')

        if task == 'summary':

            conference_id = payload.get('conference_id')
            if conference_id:
                try:
                    conference = Conference.get(id=conference_id)
                except Conference.DoesNotExist:
                    raise PMError(status=400, app_error=CONFERENCE_NOT_FOUND)

                JobWebhookView.build_conference_summary(conference)

                # if we should trigger a cleanup
                if settings.POST_CONFERENCE_CLEANUP:
                    # delete all stats events
                    conference.events.filter(type='stats').delete()

                log.info('Finished building summary for conference: {}'.format(conference_id))

                return JSONHttpResponse(content={})

        raise PMError(status=404)

    @staticmethod
    def build_conference_summary(conference):
        # if the conf already has a summary attached, reuse it
        if hasattr(conference, 'summary'):
            summary = conference.summary
            summary.status = SUMMARY_STATUS_ENUM['ongoing']
        else:
            summary = Summary(conference=conference, status=SUMMARY_STATUS_ENUM['ongoing'])

        # save it here so we have he ongoing flag set
        # and to announce the user that a summary is building
        summary.save()

        try:
            if CURRENT_SUMMARY_VERSION == 1:
                summary.data = JobWebhookView.v1_summary(conference)
                JobWebhookView.check_emos_score(summary.data)

            summary.status = SUMMARY_STATUS_ENUM['done']
            summary.end_time = datetime.utcnow()
        except Exception as e:
            log.warning(e)
            summary.status = SUMMARY_STATUS_ENUM['error']

        # save it again when done
        summary.save()

    def get_stats_events(conference):

        try:
            # use the native query because it's faster to handle the resulting payload
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM app_genericevent WHERE conference_id = %s AND type = %s", 
                    [conference.id, 'stats']
                )

                events = dictfetchall(cursor)

        except Exception as e:
            log.warning('Native query for stats events failed. Using django ORM.')

            # if it fails, use django's ORM
            events = EventView.query_events(
                event_type='stats',
                conference=conference,
            )

            # transform into dicts so it's faster to handle
            events = [e.__dict__ for e in events]

        return events

    @staticmethod
    def v1_summary(conference):
        events = JobWebhookView.get_stats_events(conference)

        # response object that will be encoded and returned
        response_object = {}

        events = list(events)
        events.reverse()

        for event in events:
            connection_id = str(event.get('connection_id'))
            event_data = event.get('data', {})

            if event_data.get('connection'):
                connection_data = event_data.get('connection')

                # log.info('adding connection {}'.format(connection_id))
                response_object[connection_id] = response_object.get(connection_id, [])

                response_object[connection_id].append({
                    'id': str(event.get('id')),
                    'app': str(event.get('app_id')),
                    'session': str(event.get('session_id')),
                    'conference': str(event.get('conference_id')),
                    'participant': str(event.get('participant_id')),
                    'peer': str(event.get('peer_id')),
                    'connection': str(event.get('connection_id')),
                    'created_at': str(event.get('created_at')),
                    'type': event.get('type'),
                    'data': {
                        'connection': {
                            'id': connection_data.get('id'),
                            'bytesSent': connection_data.get('bytesSent'),
                            'packetsSent': connection_data.get('packetsSent'),
                            'responsesReceived': connection_data.get('responsesReceived'),
                            'totalRoundTripTime': connection_data.get('totalRoundTripTime'),
                        },
                        'remote': event_data.get('remote', {}),
                        'audio': {
                            'inbound': [],
                            'outbound': []
                        },
                        'video': {
                            'inbound': [],
                            'outbound': []
                        }
                    }
                })

            if event_data.get('track'):

                emos_score = None
                try:
                    emos_score = JobWebhookView.compute_emos(event_data, response_object[connection_id][-1]['data']['remote'])
                except Exception as e:
                    log.error(f'Error while processing data for eMOS score: {e}')
                    pass

                track_kind = event_data.get('kind')
                track_direction = keys.get(event_data.get('type'))

                track_data = {
                    'id': event_data.get('id'), 
                    'mediaType': event_data.get('mediaType'),
                }

                if track_direction == 'inbound':
                    track_data['headerBytesReceived'] = event_data.get('headerBytesReceived')
                    track_data['bytesReceived'] = event_data.get('bytesReceived')
                    track_data['packetsReceived'] = event_data.get('packetsReceived')
                    track_data['packetsLost'] = event_data.get('packetsLost')
                    track_data['jitter'] = event_data.get('jitter')
                    track_data['emos'] = emos_score

                elif track_direction == 'outbound':
                    track_data['packetsSent'] = event_data.get('packetsSent')
                    track_data['headerBytesSent'] = event_data.get('headerBytesSent')
                    track_data['bytesSent'] = event_data.get('bytesSent')

                if track_kind == 'video':
                    track_data['frameWidth'] = event_data.get('frameWidth')
                    track_data['frameHeight'] = event_data.get('frameHeight')

                    if track_direction == 'inbound':
                        track_data['framesReceived'] = event_data.get('framesReceived')
                        track_data['framesDecoded'] = event_data.get('framesDecoded')
                        track_data['totalDecodeTime'] = event_data.get('totalDecodeTime')

                    elif track_direction == 'outbound':
                        track_data['framesSent'] = event_data.get('framesSent')
                        track_data['framesEncoded'] = event_data.get('framesEncoded')
                        track_data['totalEncodeTime'] = event_data.get('totalEncodeTime')

                try:
                    response_object[connection_id][-1]['data'][track_kind][track_direction].append(track_data)
                except Exception as e:
                    pass

        # concatenate arrays
        final = []
        for a in response_object.values():
            final += a

        return sorted(final, key=lambda ev: ev['created_at'])

    @staticmethod
    def compute_emos(event_data, remote):

        # we only care about track data
        if event_data.get('track'):

            track_kind = event_data.get('kind')
            track_direction = keys.get(event_data.get('type'))
            track_id = event_data.get('id')

            # if audio
            if track_kind == 'audio':

                # if inbound
                if track_direction == 'inbound':

                    packetloss = None
                    round_trip_time = None

                    tracks = remote.get('audio', {}).get('outbound', [])
                    outbound_audio_track = [t for t in tracks if t.get('localId') == track_id]

                    # if we have remote stats
                    if len(outbound_audio_track) == 1:
                        # rtt is in seconds
                        round_trip_time = outbound_audio_track[0].get('roundTripTime', 0) * 1000

                        packets_sent = outbound_audio_track[0].get('packetsSent')
                        packets_received = event_data.get('packetsReceived')

                        # make sure we have packets_sent
                        if packets_sent is not None:
                            packetloss = (packets_sent - packets_received) / packets_sent
                            packetloss = max(packetloss, 0)
                        else:
                            # without we can just return
                            return None

                    else:
                        # without remote track no need to continue
                        return None

                    buffer_delay = 0
                    if event_data.get('jitterBufferEmittedCount') is not None and event_data.get('jitterBufferDelay') is not None:
                        buffer_delay = ( event_data.get('jitterBufferDelay') / event_data.get('jitterBufferEmittedCount') ) * 1000

                    delay = 20 + buffer_delay + round_trip_time

                    r0 = 100

                    # TODO: add dtx detection
                    Ie = 6
                    if event_data.get('bitrate'):
                        Ie = clamp(55 - 4.6 * math.log(event_data.get('bitrate')), 0, 30)

                    Bpl = 20 if event_data.get('fecPacketsReceived') else 10
                    Ipl = Ie + (100 - Ie) * (packetloss / (packetloss + Bpl))

                    aux = 0.1 * delay - 150 if delay > 150 else 0
                    Id = delay * 0.03 + aux

                    R = clamp(r0 - Ipl - Id, 0, 100)

                    MOS = 1 + 0.035 * R + (R * (R - 60) * (100 - R) * 7) / 1000000

                    return clamp(round(MOS * 100) / 100, 1, 5)


    @staticmethod
    def check_emos_score(summary):
        """
        Used to check if the participant / conference had problems due to low emos
        and save an issue if so

        TODO: refactor this function. not very pretty :\
        """

        issues = {
            'low': {},
            'very_low': {},
        }

        issue_template = {
            'audio': {
                'session': None,
                'conference': None,
                'count': 0,
                'average': 0
            },
            'video': {
                'session': None,
                'conference': None,
                'count': 0,
                'average': 0
            }
        }

        # if an emos score was detected for more than 30 seconds
        min_score = 30000 / settings.DEFAULT_INTERVAL

        def update_score(issue, score):
            issue['count'] += 1

            if not issue['average']:
                issue['average'] = score

            issue['average'] = (issue['average'] + score) / 2

            issue['session'] = report.get('session')
            issue['conference'] = report.get('conference')


        for report in summary:
            inbound_audio = report.get('data').get('audio').get('inbound')
            
            # check all inbound audio tracks eMOS
            for track in inbound_audio:
                score = track.get('emos')
                participant_id = report.get('participant')
                
                # if we've computed the score
                if not score:
                    continue

                # if the score is bellow 3 = really bad exp
                if score < 3:
                    issue = issues['very_low'].get(participant_id, issue_template)

                    update_score(issue['audio'], score)

                    issues['very_low'][participant_id] = issue

                # bellow 4 is not ideal
                elif score < 4:
                    issue = issues['low'].get(participant_id, issue_template)

                    update_score(issue['audio'], score)

                    issues['low'][participant_id] = issue


        # loop through issues and see if participants had prolonged problems
        for participant_id, issue in issues['low'].items():
            if issue['audio']['count'] >= min_score:
                Issue(
                    code='low_emos',
                    type=Issue.TYPES_OF_ISSUES['warning'],
                    participant=Participant(id=participant_id),
                    session=Session(id=issue['audio']['session']),
                    conference=Conference(id=issue['audio']['conference']),
                    data={'average': issue['audio']['average']},
                ).save()

        for participant_id, issue in issues['very_low'].items():
            if issue['audio']['count'] >= min_score:
                Issue(
                    code='very_low_emos',
                    type=Issue.TYPES_OF_ISSUES['error'],
                    participant=Participant(id=participant_id),
                    session=Session(id=issue['audio']['session']),
                    conference=Conference(id=issue['audio']['conference']),
                    data={'average': issue['audio']['average']},
                ).save()
