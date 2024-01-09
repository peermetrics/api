from .event_view import EventView


class BrowserEventView(EventView):
    event_category = 'browser'
    require_peer_id = False
