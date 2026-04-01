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

    @staticmethod
    def get_stats_events(conference):

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM app_genericevent WHERE conference_id = %s AND type = %s ORDER BY created_at ASC, id ASC",
                    [conference.id, 'stats']
                )

                events = dictfetchall(cursor)

        except Exception as e:
            log.warning('Native query for stats events failed. Using django ORM.')

            events = EventView.query_events(
                event_type='stats',
                conference=conference,
            ).order_by('created_at', 'id')

            events = [e.__dict__ for e in events]

        return events

    @staticmethod
    def build_track_data(track_stats, direction, track_type):
        """Pure helper that builds a summary track_data dict from raw track stats."""
        track_data = {
            'id': track_stats.get('id'),
            'mediaType': track_stats.get('mediaType'),
        }

        if direction == 'inbound':
            track_data['headerBytesReceived'] = track_stats.get('headerBytesReceived')
            track_data['bytesReceived'] = track_stats.get('bytesReceived')
            track_data['packetsReceived'] = track_stats.get('packetsReceived')
            track_data['packetsLost'] = track_stats.get('packetsLost')
            track_data['jitter'] = track_stats.get('jitter')

        elif direction == 'outbound':
            track_data['packetsSent'] = track_stats.get('packetsSent')
            track_data['headerBytesSent'] = track_stats.get('headerBytesSent')
            track_data['bytesSent'] = track_stats.get('bytesSent')

        if track_type == 'video':
            track_data['frameWidth'] = track_stats.get('frameWidth')
            track_data['frameHeight'] = track_stats.get('frameHeight')

            if direction == 'inbound':
                track_data['framesReceived'] = track_stats.get('framesReceived')
                track_data['framesDecoded'] = track_stats.get('framesDecoded')
                track_data['totalDecodeTime'] = track_stats.get('totalDecodeTime')

            elif direction == 'outbound':
                track_data['framesSent'] = track_stats.get('framesSent')
                track_data['framesEncoded'] = track_stats.get('framesEncoded')
                track_data['totalEncodeTime'] = track_stats.get('totalEncodeTime')

        return track_data

    @staticmethod
    def _append_track_event(event_data, response_object, connection_id):
        """Append a per-track event to the latest snapshot for this connection."""
        if connection_id not in response_object or not response_object[connection_id]:
            return False

        snapshot = response_object[connection_id][-1]
        remote = snapshot['data']['remote']

        emos_score = None
        try:
            emos_score = JobWebhookView.compute_emos(event_data, remote)
        except Exception as e:
            log.error(f'Error while processing data for eMOS score: {e}')

        track_kind = event_data.get('kind')
        track_direction = keys.get(event_data.get('type'))

        track_data = JobWebhookView.build_track_data(
            event_data, track_direction, track_kind)

        if track_direction == 'inbound':
            track_data['emos'] = emos_score

        try:
            snapshot['data'][track_kind][track_direction].append(track_data)
        except (KeyError, TypeError):
            pass

        return True

    @staticmethod
    def v1_summary(conference):
        events = JobWebhookView.get_stats_events(conference)

        response_object = {}
        pending_tracks = {}

        events = list(events)

        for event in events:
            connection_id = str(event.get('connection_id'))
            event_data = event.get('data', {})

            if event_data.get('connection'):
                connection_data = event_data.get('connection')

                response_object[connection_id] = response_object.get(connection_id, [])

                snapshot = {
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
                }

                remote = event_data.get('remote', {})

                for track_type in ['audio', 'video']:
                    for direction in ['inbound', 'outbound']:
                        inline_tracks = event_data.get(track_type, {}).get(direction, [])
                        for track_stats in inline_tracks:
                            track_data = JobWebhookView.build_track_data(
                                track_stats, direction, track_type)

                            if track_type == 'audio' and direction == 'inbound':
                                try:
                                    emos_score = JobWebhookView.compute_emos(
                                        track_stats, remote)
                                except Exception as e:
                                    log.error(f'Error computing eMOS for inline track: {e}')
                                    emos_score = None
                                track_data['emos'] = emos_score

                            snapshot['data'][track_type][direction].append(track_data)

                response_object[connection_id].append(snapshot)

                # Flush any track events that arrived before this snapshot
                for pending_event_data in pending_tracks.pop(connection_id, []):
                    JobWebhookView._append_track_event(
                        pending_event_data, response_object, connection_id)

            if 'track' in event_data:
                if connection_id in response_object and response_object[connection_id]:
                    JobWebhookView._append_track_event(
                        event_data, response_object, connection_id)
                else:
                    pending_tracks.setdefault(connection_id, []).append(event_data)

        final = []
        for a in response_object.values():
            final += a

        return sorted(final, key=lambda ev: ev['created_at'])

    @staticmethod
    def compute_emos(event_data, remote):

        if 'track' not in event_data:
            return None

        track_kind = event_data.get('kind')
        track_direction = keys.get(event_data.get('type'))
        track_id = event_data.get('id')

        if track_kind != 'audio' or track_direction != 'inbound':
            return None

        packets_received = event_data.get('packetsReceived', 0) or 0
        packets_lost = event_data.get('packetsLost', 0) or 0
        total_packets = packets_received + packets_lost

        if total_packets == 0:
            return None

        # Prefer remote-outbound-rtp packetsSent for packet loss (more accurate),
        # fall back to local packetsLost / (packetsLost + packetsReceived)
        packetloss = None
        outbound_tracks = remote.get('audio', {}).get('outbound', [])
        outbound_match = [t for t in outbound_tracks if t.get('localId') == track_id]

        if len(outbound_match) == 1:
            packets_sent = outbound_match[0].get('packetsSent')
            if packets_sent is not None and packets_sent > 0:
                packetloss = max((packets_sent - packets_received) / packets_sent, 0)

        if packetloss is None:
            packetloss = packets_lost / total_packets

        # RTT from remote-inbound-rtp (carries roundTripTime, unlike remote-outbound-rtp)
        round_trip_time = 0
        for rit in remote.get('audio', {}).get('inbound', []):
            if rit.get('roundTripTime') is not None:
                round_trip_time = rit.get('roundTripTime') * 1000
                break

        buffer_delay = 0
        emitted_count = event_data.get('jitterBufferEmittedCount')
        jitter_delay = event_data.get('jitterBufferDelay')
        if emitted_count is not None and jitter_delay is not None and emitted_count > 0:
            buffer_delay = (jitter_delay / emitted_count) * 1000

        # E-model expects one-way mouth-to-ear delay
        delay = 20 + buffer_delay + (round_trip_time / 2)

        r0 = 100

        Ie = 6
        bitrate = event_data.get('bitrate')
        if bitrate and bitrate > 0:
            Ie = clamp(55 - 4.6 * math.log(bitrate), 0, 30)

        Bpl = 20 if event_data.get('fecPacketsReceived') else 10
        Ipl = Ie + (100 - Ie) * (packetloss / (packetloss + Bpl))

        aux = 0.1 * (delay - 150) if delay > 150 else 0
        Id = delay * 0.03 + aux

        R = clamp(r0 - Ipl - Id, 0, 100)

        MOS = 1 + 0.035 * R + (R * (R - 60) * (100 - R) * 7) / 1000000

        return clamp(round(MOS * 100) / 100, 1, 5)

    @staticmethod
    def check_emos_score(summary):
        """
        Used to check if the participant / conference had problems due to low emos
        and save an issue if so
        """

        def make_issue_template():
            return {
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

        issues = {
            'low': {},
            'very_low': {},
        }

        # if an emos score was detected for more than 30 seconds
        min_score = 30000 / settings.DEFAULT_INTERVAL

        def update_score(issue, score):
            issue['count'] += 1
            # Welford's online mean
            issue['average'] = issue['average'] + (score - issue['average']) / issue['count']

            issue['session'] = report.get('session')
            issue['conference'] = report.get('conference')

        for report in summary:
            inbound_audio = report.get('data', {}).get('audio', {}).get('inbound', [])

            for track in inbound_audio:
                score = track.get('emos')
                participant_id = report.get('participant')

                if not score:
                    continue

                if score < 3:
                    if participant_id not in issues['very_low']:
                        issues['very_low'][participant_id] = make_issue_template()

                    update_score(issues['very_low'][participant_id]['audio'], score)

                elif score < 4:
                    if participant_id not in issues['low']:
                        issues['low'][participant_id] = make_issue_template()

                    update_score(issues['low'][participant_id]['audio'], score)

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
