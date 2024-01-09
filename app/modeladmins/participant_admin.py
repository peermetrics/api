from django.contrib import admin

from ..models.app import App
from ..models.conference import Conference


class ParticipantAdmin(admin.ModelAdmin):
    readonly_fields = ('app', 'conferences')
    list_display = ['id', 'participant_id', 'participant_name', 'link_to_conference', 'link_to_app', 'created_at']
    search_fields = ['id', 'participant_id', 'participant_name', 'app__id']
    view_on_site = False
    ordering = ('-created_at',)

    def link_to_conference(self, obj):
        return Conference.link_to_admin(Conference.get_type(), obj.conference_id) if hasattr(obj, 'conference_id') else None
    link_to_conference.short_description = 'Conference'

    def link_to_app(self, obj):
        return App.link_to_admin(App.get_type(), obj.app_id)
    link_to_app.short_description = 'App'
