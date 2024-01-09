
from django.contrib import admin


class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'created_at']
    search_fields = ['id', 'name', 'owner__id']
    view_on_site = False
    ordering = ('-created_at',)
