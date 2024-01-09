from django.urls import path
from django.conf import settings

from .views.apps_reset_api_key_view import AppsResetApiKeyView
from .views.apps_view import AppsView
from .views.browser_event_view import BrowserEventView
from .views.conference_view import ConferencesView
from .views.connection_event_view import ConnectionEventView
from .views.connection_view import ConnectionView
from .views.issue_view import IssueView
from .views.connection_event_batch_view import ConnectionEventBatchView
from .views.get_user_media_event_view import GetUserMediaEventView
from .views.initialize_view import InitializeView
from .views.teapot_view import TeapotView
from .views.organizations_view import OrganizatonsView
from .views.participant_view import ParticipantsView
from .views.search_view import SearchView
from .views.get_url_view import GetUrlView
from .views.stop_conference_view import StopConferenceView

from .views.session_view import SessionView
from .views.stats_view import StatsView
from .views.conference_events_view import ConferenceEventsView
from .views.conference_graph_view import ConferenceGraphView
from .views.job_webhook_view import JobWebhookView
from .views.track_view import TracksView

urlpatterns = [
    path('initialize', InitializeView.as_view(), name='initialize'),

    path('events/get-user-media', GetUserMediaEventView.as_view(), name='events-getusermedia'),
    path('events/browser', BrowserEventView.as_view(), name='events-browser'),

    # DEPRECATED
    path('connection', ConnectionEventView.as_view(), name='connection'),
    path('connection/batch', ConnectionEventBatchView.as_view(), name='connection-batch'),

    path('connections', ConnectionView.as_view(), name='connections'),
    path('connections/<uuid:pk>', ConnectionView.as_view(), name='connection'),
    path('issues', IssueView.as_view(), name='issues'),
    path('issues/<uuid:pk>', IssueView.as_view(), name='issue'),

    path('stats', StatsView.as_view(), name='stats'),
    path('tracks', TracksView.as_view(), name='tracks'),

    path('sessions', SessionView.as_view(), name='sessions'),
    path('sessions/<uuid:pk>', SessionView.as_view(), name='session'),

    path('organizations', OrganizatonsView.as_view(), name='organizations'),
    path('organizations/<uuid:pk>', OrganizatonsView.as_view(), name='organization'),

    path('apps', AppsView.as_view(), name='apps'),
    path('apps/<uuid:pk>', AppsView.as_view(), name='app'),

    path('apps/<uuid:pk>/reset-key', AppsResetApiKeyView.as_view(), name='app-reset-key'),

    path('conferences', ConferencesView.as_view(), name='conferences'),
    path('conferences/<uuid:pk>', ConferencesView.as_view(), name='conference'),
    path('conferences/<uuid:pk>/events', ConferenceEventsView.as_view(), name='conference-events'),
    path('conferences/<uuid:pk>/graphs', ConferenceGraphView.as_view(), name='conference-graphs'),

    path('participants', ParticipantsView.as_view(), name='participants'),
    path('participants/<uuid:pk>', ParticipantsView.as_view(), name='participant'),

    # Webhooks
    path('webhooks/jobs', JobWebhookView.as_view(), name='job-webhook'),

    path('search', SearchView.as_view(), name='search'),
    path('services/get-url', GetUrlView.as_view(), name='services-get-url'),
    path('services/stop-conference', StopConferenceView.as_view(), name='services-stop-confence'),

    path('teapot', TeapotView.as_view(), name='teapot'),
]

