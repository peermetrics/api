from .event_view import EventView


class ConnectionEventView(EventView):
    event_category = 'connection'
    require_peer_id = True
