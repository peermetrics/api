
from django.contrib import admin

from ..models.app import App

class ConferenceAdmin(admin.ModelAdmin):
    readonly_fields = ('app',)
    list_display = ['id', 'conference_id', 'conference_name', 'link_to_app', 'created_at']
    search_fields = ['id', 'conference_id', 'conference_name', 'app__id']
    view_on_site = False
    ordering = ('-created_at',)

    def link_to_app(self, obj):
        return App.link_to_admin(App.get_type(), obj.app_id)
    link_to_app.short_description = 'App'
