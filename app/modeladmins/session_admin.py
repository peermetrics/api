from django.contrib import admin

from ..models.conference import Conference
from ..models.participant import Participant


class SessionAdmin(admin.ModelAdmin):
    readonly_fields = ('conference', 'participant')
    list_display = ['id', 'link_to_conference', 'link_to_participant', 'created_at']
    search_fields = ['id', 'conference__id', 'participant__id', 'conference__app__id']
    view_on_site = False
    ordering = ('-created_at',)

    def link_to_conference(self, obj):
        return Conference.link_to_admin(Conference.get_type(), obj.conference_id)
    link_to_conference.short_description = 'Conference'

    def link_to_participant(self, obj):
        return Participant.link_to_admin(Participant.get_type(), obj.participant_id)
    link_to_participant.short_description = 'Participant'
