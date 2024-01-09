from django.contrib import admin

from ..models.conference import Conference


class SummaryAdmin(admin.ModelAdmin):
    readonly_fields = ('conference',)
    list_display = ['id', 'link_to_conference', 'status', 'created_at', 'end_time', 'version']
    search_fields = ['id', 'conference__id']
    view_on_site = False
    ordering = ('-created_at',)

    def link_to_conference(self, obj):
        return Conference.link_to_admin(Conference.get_type(), obj.conference_id)
    link_to_conference.short_description = 'Conference'

