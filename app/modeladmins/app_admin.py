from django.contrib import admin

from ..models.organization import Organization


class AppAdmin(admin.ModelAdmin):
    readonly_fields = ('organization',)
    list_display = ['id', 'name', 'link_to_org', 'recording', 'created_at']
    search_fields = ['id', 'organization__id', 'name', 'organization__owner__id']
    view_on_site = False

    def link_to_org(self, obj):
        return Organization.link_to_admin(Organization.get_type(), obj.organization_id)
    link_to_org.short_description = 'Organization'
