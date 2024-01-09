from django.contrib import admin

from .models.app import App
from .models.conference import Conference
from .models.connection import Connection
from .models.generic_event import GenericEvent
from .models.issue import Issue
from .models.organization import Organization
from .models.participant import Participant
from .models.session import Session
from .models.summary import Summary
from .models.track import Track
from .models.user import User

from .modeladmins.app_admin import AppAdmin
from .modeladmins.conference_admin import ConferenceAdmin
from .modeladmins.connection_admin import ConnectionAdmin
from .modeladmins.generic_event_admin import GenericEventAdmin
from .modeladmins.issue_admin import IssueAdmin
from .modeladmins.track_admin import TrackAdmin
from .modeladmins.organization_admin import OrganizationAdmin
from .modeladmins.participant_admin import ParticipantAdmin
from .modeladmins.session_admin import SessionAdmin
from .modeladmins.summary_admin import SummaryAdmin


admin.site.register(Conference, ConferenceAdmin)
admin.site.register(GenericEvent, GenericEventAdmin)
admin.site.register(Participant, ParticipantAdmin)
admin.site.register(Session, SessionAdmin)
admin.site.register(Connection, ConnectionAdmin)
admin.site.register(Issue, IssueAdmin)
admin.site.register(Track, TrackAdmin)
admin.site.register(Summary, SummaryAdmin)

admin.site.register(App, AppAdmin)
admin.site.register(Organization, OrganizationAdmin)
admin.site.register(User)
