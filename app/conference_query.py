"""
Query helpers for Conference-related aggregates.

Peers created only for addConnection (P2P remote) are linked on conference.participants
but often have no Session and no name; they are excluded. SFU endpoints (is_sfu) are
excluded from participant totals — only human/clients with a session in the conference
are counted.
"""

from django.db.models import Count, F, Q

PARTICIPANTS_COUNT_ANNOTATION = Count(
    'participants',
    filter=Q(participants__is_active=True)
    & Q(participants__is_sfu=False)
    & Q(participants__sessions__conference_id=F('id')),
    distinct=True,
)
