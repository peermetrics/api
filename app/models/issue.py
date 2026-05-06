import datetime
import uuid

from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models import Q

from .basemodel import BaseModel


def _positive_stat_counter(val):
    try:
        return float(val) > 0
    except (TypeError, ValueError):
        return False


def _candidate_pair_stats_indicate_established(conn):
    """
    RTC candidate-pair stats (merged into parsed stats connection block): require
    succeeded plus a signal that the pair is actually in use, not only reported.
    """
    if not isinstance(conn, dict) or conn.get('state') != 'succeeded':
        return False
    if conn.get('nominated') is True:
        return True
    if conn.get('selected') is True:
        return True
    if _positive_stat_counter(conn.get('bytesSent')) or _positive_stat_counter(conn.get('bytesReceived')):
        return True
    if conn.get('currentRoundTripTime') is not None:
        return True
    return False


def _stats_payload_indicates_established(data):
    """
    True only when parsed stats show ICE completion or media counters advancing —
    not the first getStats() poll right after RTCPeerConnection creation (those rows
    still use type=stats and carry minimal / empty connection snapshots).
    """
    if not isinstance(data, dict):
        return False

    conn = data.get('connection')
    if isinstance(conn, dict):
        if _candidate_pair_stats_indicate_established(conn):
            return True
        if _positive_stat_counter(conn.get('bytesReceived')) or _positive_stat_counter(
            conn.get('bytesSent')
        ):
            return True
        local_ct = (conn.get('local') or {}).get('candidateType')
        remote_ct = (conn.get('remote') or {}).get('candidateType')
        if local_ct and remote_ct:
            return True

    def media_blocks_have_traffic(block):
        if not isinstance(block, dict):
            return False
        for direction in ('inbound', 'outbound'):
            reports = block.get(direction)
            if not isinstance(reports, list):
                continue
            for report in reports:
                if not isinstance(report, dict):
                    continue
                if (
                    _positive_stat_counter(report.get('bytesReceived'))
                    or _positive_stat_counter(report.get('bytesSent'))
                    or _positive_stat_counter(report.get('packetsReceived'))
                    or _positive_stat_counter(report.get('packetsSent'))
                ):
                    return True
        return False

    for kind in ('audio', 'video'):
        if media_blocks_have_traffic(data.get(kind)):
            return True

    remote = data.get('remote')
    if isinstance(remote, dict):
        for kind in ('audio', 'video'):
            if media_blocks_have_traffic(remote.get(kind)):
                return True

    # Per-track stats rows (StatsView.save_event for each track) — flat RTP-ish dict
    if (
        _positive_stat_counter(data.get('bytesReceived'))
        or _positive_stat_counter(data.get('bytesSent'))
        or _positive_stat_counter(data.get('packetsReceived'))
        or _positive_stat_counter(data.get('packetsSent'))
    ):
        return True

    return False


ISSUES = {
    # ERRORS
    'no_media_access': {
        'title': 'Could not access any media device',
        'explanation': 'The app could not access any input device from the browser during a session.'
    },
    'ice_failed': {
        'title': 'Connection could not be established',
        'explanation': 'The user could not find any suitable ICE candidates to establish a connection to another participant or a SFU.'
    },
    'no_connection': {
        'title': 'The participant could not establish a connection',
        'explanation': 'There was a session for this participant that no connection could be established to another participant or a SFU.'
    },
    'very_low_emos': {
        'title': 'The participant had a very bad experience during the conference',
        'explanation': 'Due to network conditions, this participant had a poor experience with incoming content. Causes might have been robotic audio, frozen video, etc.'
    },
    # WARNINGS
    'getusermedia_error': {
        'title': 'Problem accessing media',
        'explanation': 'The user had a problem accessing the mic/camera of the device.'
    },
    'icecandidateerror': {
        'title': 'ICE candidate error',
        'explanation': ''
    },
    'connection_disconnected': {
        'title': 'Connection disconnected',
        'explanation': 'An user temporarily disconnected.'
    },
    'connection_failed': {
        'title': 'Connection failed',
        'explanation': ''
    },
    'multiple_rejoins': {
        'title': 'Multiple rejoins',
        'explanation': 'An user refreshed during a call.'
    },
    'tcp_used': {
        'title': 'Media sent over TCP',
        'explanation': 'Participant used the TCP protocol to transfer media instead of UDP.'
    },
    'turn_used': {
        'title': 'Connection relayed through a TURN server',
        'explanation': 'The participant might be behind an asymmetric NAT and connection could not be established directly.'
    },
    'low_emos': {
        'title': 'Participant had a less than ideal experience',
        'explanation': 'During the conference, the participant might have experienced periods of bad incoming audio quality or frozen video.'
    }
}

TYPES_OF_ISSUES = {
    'warning': 'w',
    'error': 'e',
}

class Issue(BaseModel):
    """
    An issue is model containing the details of  an issue that appeared during a conference, session, etc.

    Attrs:
        cache_keys: combinations of fields used to compose the keys used to cache the object

    Fields:
        id: ID from db, UUID
        session: the session linked to the issue, fk
        participant: the participant linked to the issue, fk
        conference: the conference linked to the issue, fk
        events: the events linked to the issue, fk
        connection: the connection linked to the issue, fk
        track: the track linked to the issue, fk
        data: info related to the issue, dict
        type: the issue type, string
        code: the issue code, string
    """
    TYPES_OF_ISSUES = TYPES_OF_ISSUES

    class Meta:
        indexes = [
            models.Index(fields=['conference', 'type'], name='idx_issue_conf_type'),
        ]

    cache_keys = (
        sorted(('id',)),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    session = models.ForeignKey('Session', on_delete=models.CASCADE, null=False, related_name='issues')
    conference = models.ForeignKey('Conference', on_delete=models.CASCADE, null=True, blank=True, related_name='issues')
    participant = models.ForeignKey('Participant', on_delete=models.CASCADE, null=True, blank=True, related_name='issues')
    events = models.ManyToManyField('GenericEvent', blank=True, default=None, related_name='issues')
    connection = models.ForeignKey('Connection', on_delete=models.CASCADE, null=True, blank=True, related_name='issues')
    track = models.ForeignKey('Track', on_delete=models.CASCADE, null=True, blank=True, related_name='issues')

    type = models.CharField(
        max_length=1, null=False,
        choices=tuple([(TYPES_OF_ISSUES[key], key) for key in TYPES_OF_ISSUES.keys()]),
    )
    code = models.CharField(max_length=32, null=False)
    data = JSONField(null=True, blank=True)

    created_at = models.DateTimeField(default=datetime.datetime.utcnow)
    is_active = models.BooleanField(default=True)

    @property
    def title(self):
        return ISSUES.get(self.code).get('title')

    @property
    def explanation(self):
        return ISSUES.get(self.code).get('explanation')

    @staticmethod
    def check_stats(data, session, connection):
        if not data or not session or not connection:
            raise Exception('Missing check_stats parameters')

        protocol = data.get('local', {}).get('protocol')
        local_candidate_type = data.get('local', {}).get('candidateType')

        # if the protocol is tcp we haven't saved an issue already
        if protocol == 'tcp' and not connection.connection_info['detected_tcp']:
            Issue(
                code='tcp_used',
                type=TYPES_OF_ISSUES['warning'],
                session=session,
                participant=session.participant,
                connection=connection,
                conference=session.conference,
            ).save()

            connection.connection_info['detected_tcp'] = True
            connection.save()

        # if the user has been using a turn for this connection
        if local_candidate_type == 'relay' and not connection.connection_info['detected_turn']:
            Issue(
                code='turn_used',
                type=TYPES_OF_ISSUES['warning'],
                session=session,
                participant=session.participant,
                connection=connection
            ).save()

            connection.connection_info['detected_turn'] = True
            connection.save()

    @staticmethod
    def check_end_session(session):
        """
        Used to check if we had issues at the end of a session.
        Check if we:
        - All getUserMedia requests have failed
        - Could not connect to peer
        """

        # 1. Checking getUserMedia requests
        get_user_media_requests = 0
        failed_get_user_media_requests = 0
        for event in session.events.filter(type='getUserMedia'):
            if event.data.get('constraints'):
                get_user_media_requests += 1

            if event.data.get('error'):
                failed_get_user_media_requests += 1

        if get_user_media_requests > 0 and get_user_media_requests == failed_get_user_media_requests:
            Issue(
                code='no_media_access',
                type=TYPES_OF_ISSUES['error'],
                session=session,
                participant=session.participant,
                conference=session.conference,
            ).save()

        # 2. Checking connections
        # we're looking if all connections are in an unfinished state
        connection_bad_state = ['new', 'connecting', 'failed']
        connections = session.connections.all()
        # Only stats batches that actually show ICE/RTP progress (not an empty early poll).
        connection_ids_with_establishing_stats = set()
        for ev in session.events.filter(type='stats').exclude(connection_id=None).only(
            'connection_id', 'data'
        ):
            if ev.data and _stats_payload_indicates_established(ev.data):
                connection_ids_with_establishing_stats.add(ev.connection_id)
        # If the peer leaves, the PC often ends in failed while rows still look "unfinished".
        # Once we logged connected/completed, do not treat as never-connected.
        connection_ids_ever_established = set(
            session.events.filter(
                Q(type='onconnectionstatechange', data='connected')
                | Q(type='oniceconnectionstatechange', data='connected')
                | Q(type='oniceconnectionstatechange', data='completed'),
            )
            .exclude(connection_id=None)
            .values_list('connection_id', flat=True)
        )
        established_ids = connection_ids_with_establishing_stats | connection_ids_ever_established
        # if the user had at least one connection
        if len(connections) > 0:
            bad_conns = [
                c for c in connections
                if c.state in connection_bad_state and c.id not in established_ids
            ]

            if len(connections) == len(bad_conns):
                Issue(
                    code='no_connection',
                    type=TYPES_OF_ISSUES['error'],
                    session=session,
                    participant=session.participant,
                    conference=session.conference,
                ).save()

    @staticmethod
    def get_type():
        return 'issue'

    def __str__(self):
        return str(self.id)
