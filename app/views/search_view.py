from .generic_view import GenericView
from ..utils import JSONHttpResponse, validate_string
from ..errors import PMError, INVALID_PARAMETERS
from ..models.conference import Conference
from ..models.participant import Participant
from ..models.app import App
from ..models.organization import Organization

from django.contrib.postgres.search import TrigramSimilarity
from django.conf import settings


class SearchView(GenericView):
    """
    API endpoint used for the search functionality. Uses the trigram similarity from postgres to achieve inexact queries
    and to sort the output based on similarity.
    """

    @classmethod
    def get(cls, request):
        """
        Receives an HTTP request containing a search query and responds with the most similar MAX_SEARCH_RESULTS
        results.

        :param request: the HTTP request
        """

        query = validate_string(request.GET.get('query'))

        if not query or len(query) > 64:
            raise PMError(status=400, app_error=INVALID_PARAMETERS)

        matches = []

        matches.extend(
            Conference.objects.filter(
                conference_id__trigram_similar=query,
            ).annotate(similarity=TrigramSimilarity('conference_id', query)),
        )
        matches.extend(
            Conference.filter(
                conference_name__trigram_similar=query,
            ).annotate(similarity=TrigramSimilarity('conference_name', query)),
        )
        matches.extend(
            Participant.filter(
                participant_id__trigram_similar=query,
            ).annotate(similarity=TrigramSimilarity('participant_id', query)),
        )
        matches.extend(
            Participant.filter(
                participant_name__trigram_similar=query,
            ).annotate(similarity=TrigramSimilarity('participant_name', query)),
        )
        matches.extend(
            App.filter(
                api_key__trigram_similar=query,
            ).annotate(similarity=TrigramSimilarity('api_key', query)),
        )
        matches.extend(
            App.filter(
                name__trigram_similar=query,
            ).annotate(similarity=TrigramSimilarity('name', query)),
        )
        matches.extend(
            Organization.filter(
                name__trigram_similar=query,
            ).annotate(similarity=TrigramSimilarity('name', query)),
        )

        # sort the matches by similarity
        matches.sort(key=lambda x: x.similarity, reverse=True)

        # extracts the name, url and type from at most MAX_SEARCH_RESULTS matches
        matches = list(map(
            lambda x: {'name': x.get_name(), 'id':x.get_identifier(), 'url': x.get_absolute_url(), 'type': x.get_type()},
            matches[:settings.MAX_SEARCH_RESULTS],
        ))

        return JSONHttpResponse({'matches': matches})
