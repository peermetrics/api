from django.contrib import admin

from ..models.participant import Participant


class ConnectionAdmin(admin.ModelAdmin):
    readonly_fields = ('session', 'conference', 'participant', 'peer')
    list_display = ['id', 'link_to_participant', 'link_to_peer', 'type', 'state', 'created_at']
    search_fields = ['id', 'session__id']
    view_on_site = False
    ordering = ('-created_at',)

    def link_to_participant(self, obj):
        return Participant.link_to_admin(Participant.get_type(), obj.participant_id)
    link_to_participant.short_description = 'Participant'

    def link_to_peer(self, obj):
        return Participant.link_to_admin(Participant.get_type(), obj.peer_id)
    link_to_peer.short_description = 'Peer'
