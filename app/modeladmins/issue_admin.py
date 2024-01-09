from django.contrib import admin

from ..models.connection import Connection
from ..models.session import Session


class IssueAdmin(admin.ModelAdmin):
    readonly_fields = ('events', 'session', 'conference', 'participant', 'connection', 'track')

    list_display = ['id', 'link_to_session', 'link_to_connection', 'type', 'code', 'created_at']
    search_fields = ['id', 'session__id', 'connection__id', 'type', 'code']
    view_on_site = False
    ordering = ('-created_at',)

    def link_to_connection(self, obj):
        return Connection.link_to_admin(Connection.get_type(), obj.connection_id)
    link_to_connection.short_description = 'Connection'

    def link_to_session(self, obj):
        return Session.link_to_admin(Session.get_type(), obj.session_id)
    link_to_session.short_description = 'Session'
