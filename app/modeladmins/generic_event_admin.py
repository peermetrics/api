from django.contrib import admin

from ..models.conference import Conference
from ..models.connection import Connection
from ..models.participant import Participant
from ..models.session import Session
from ..models.app import App


class GenericEventAdmin(admin.ModelAdmin):
    readonly_fields = ('app', 'session', 'conference', 'participant', 'peer', 'connection', 'track')

    list_display = [
        'id', 'link_to_app', 'link_to_conference', 'link_to_participant', 'link_to_connection',
        'type', 'category', 'created_at'
    ]
    search_fields = ['id', 'conference__id', 'app__id', 'session__id', 'participant__id', 'type', 'category']
    view_on_site = False
    ordering = ('-created_at',)
    list_per_page = 20

    def link_to_conference(self, obj):
        return Conference.link_to_admin(Conference.get_type(), obj.conference_id)
    link_to_conference.short_description = 'Conference'

    def link_to_connection(self, obj):
        return Connection.link_to_admin(Connection.get_type(), obj.connection_id)
    link_to_connection.short_description = 'Connection'

    def link_to_participant(self, obj):
        return Participant.link_to_admin(Participant.get_type(), obj.participant_id)
    link_to_participant.short_description = 'Participant'

    def link_to_session(self, obj):
        return Session.link_to_admin(Session.get_type(), obj.session_id)
    link_to_session.short_description = 'Session'

    def link_to_app(self, obj):
        return App.link_to_admin(App.get_type(), obj.app_id)
    link_to_app.short_description = 'App'
