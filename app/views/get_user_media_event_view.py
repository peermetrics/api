from .event_view import EventView


class GetUserMediaEventView(EventView):
    event_category = 'getUserMedia'
    require_peer_id = False
