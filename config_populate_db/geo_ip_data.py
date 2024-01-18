GEO_IP = [
    {
        'country_code': 'US',
        'city': 'San Jose',
        'latitude': '37.34217071533203',
        'longitude': '-121.90677642822266',
    },
    {
        'country_code': 'US',
        'city': 'Quincy',
        'latitude': '47.23400115966797',
        'longitude': '-119.85199737548828',
    },
    {
        'country_code': 'US',
        'city': 'Chicago',
        'latitude': '41.84885025024414',
        'longitude': '-87.67124938964844',
    },
    {
        'country_code': 'US',
        'city': 'Manhattan',
        'latitude': '40.7589111328125',
        'longitude': '-73.97901916503906',
    },
    {
        'country_code': 'GB',
        'city': 'City of Westminster',
        'latitude': '51.50416946411133',
        'longitude': '-0.17000000178813934',
    },
    {
        'country_code': 'GB',
        'city': 'Earlsfield',
        'latitude': '51.45000076293945',
        'longitude': '-0.1833299994468689',
    },
    {
        'country_code': 'RO',
        'city': 'Bucharest',
        'latitude': '44.43655014038086',
        'longitude': '26.099349975585938',
    },
    {
        'country_code': 'IT',
        'city': 'Arese',
        'latitude': '45.541419982910156',
        'longitude': '9.067130088806152',
    },
]

GEO_IP_HEADERS = [
    {
        'X-AppEngine-City': info['city'],
        'X-AppEngine-Country': info['country_code'],
        'X-AppEngine-CityLatLong': ''.join([info['latitude'], ',', info['longitude']]),
    } for info in GEO_IP
]
