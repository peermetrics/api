import datetime
from collections import Counter, defaultdict

from django.core.exceptions import ValidationError

from ..errors import INVALID_PARAMETERS, MISSING_PARAMETERS, PMError
from ..summary_cache import cached_json
from ..utils import JSONHttpResponse
from ..models.session import Session
from .generic_view import GenericView


def _parse_iso(value):
    if value.endswith('Z'):
        value = value[:-1] + '+00:00'
    return datetime.datetime.fromisoformat(value)


class SessionSummaryView(GenericView):
    """
    Returns session counts aggregated by browser, OS, and country.
    Replaces downloading all sessions to aggregate client-side in the
    Browsers, Operating Systems, and Map charts.

    Also returns geo points (lat/lon) for rendering on the map chart.
    """

    @classmethod
    def get(cls, request):
        app_id = request.GET.get('appId')
        if not app_id:
            raise PMError(status=400, app_error=MISSING_PARAMETERS)

        filters = {
            'conference__app_id': app_id,
            'is_active': True,
        }

        created_at_gte = request.GET.get('created_at_gte')
        if created_at_gte:
            try:
                filters['created_at__gte'] = _parse_iso(created_at_gte)
            except ValueError:
                raise PMError(status=400, app_error=INVALID_PARAMETERS)

        created_at_lte = request.GET.get('created_at_lte')
        if created_at_lte:
            try:
                filters['created_at__lte'] = _parse_iso(created_at_lte)
            except ValueError:
                raise PMError(status=400, app_error=INVALID_PARAMETERS)

        def compute():
            browsers = Counter()
            oses = Counter()
            countries = Counter()
            cities = {}  # city name -> {lat, lon, count}

            try:
                rows = Session.objects.filter(**filters).values_list('platform', 'geo_ip')
                for platform, geo_ip in rows:
                    if platform:
                        browser = (platform.get('browser') or {}).get('name') or 'Unknown'
                        os_name = (platform.get('os') or {}).get('name') or 'Unknown'
                        browsers[browser] += 1
                        oses[os_name] += 1

                    if geo_ip:
                        country_code = geo_ip.get('country_code')
                        if country_code:
                            countries[country_code] += 1

                        city = geo_ip.get('city')
                        lat = geo_ip.get('latitude')
                        lon = geo_ip.get('longitude')
                        if city and lat is not None and lon is not None:
                            try:
                                lat_f = float(lat)
                                lon_f = float(lon)
                                if lat_f or lon_f:
                                    if city in cities:
                                        cities[city]['count'] += 1
                                    else:
                                        cities[city] = {
                                            'city': city,
                                            'latitude': lat_f,
                                            'longitude': lon_f,
                                            'count': 1,
                                        }
                            except (TypeError, ValueError):
                                pass
            except ValidationError:
                raise PMError(status=400, app_error=INVALID_PARAMETERS)

            return {
                'browsers': [
                    {'name': k, 'count': v}
                    for k, v in browsers.most_common()
                ],
                'os': [
                    {'name': k, 'count': v}
                    for k, v in oses.most_common()
                ],
                'countries': [
                    {'code': k, 'count': v}
                    for k, v in countries.most_common()
                ],
                'cities': list(cities.values()),
            }

        payload, _ = cached_json('sessions.summary', request, compute)
        return JSONHttpResponse(payload)
