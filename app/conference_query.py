"""
Query helpers for Conference-related aggregates.

Peers created only for addConnection (P2P remote) are linked on conference.participants
but often have no Session and no name; they are excluded. SFU endpoints (is_sfu) are
excluded from participant totals — only human/clients with a session in the conference
are counted.

participants_count must use a Subquery (not Count on the outer queryset's participants
relation): when /v1/conferences is filtered by participantId, the outer query joins
participants and would otherwise restrict the aggregate to that single participant.
"""

from django.db.models import Count, IntegerField, OuterRef, Subquery

from .models.participant import Participant

PARTICIPANTS_COUNT_SUBQUERY = Subquery(
    Participant.objects.filter(
        conferences=OuterRef('pk'),
        is_active=True,
        is_sfu=False,
        sessions__conference_id=OuterRef('pk'),
    ).order_by().values('conferences').annotate(
        cnt=Count('id', distinct=True),
    ).values('cnt')[:1],
    output_field=IntegerField(),
)
