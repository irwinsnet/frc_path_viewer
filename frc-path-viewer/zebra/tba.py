"""Functions to downloads FRC data from The Blue Alliance (TBA) API.

The functions require a TBA API authorization key, which can
be obtained by creating an account on https://www.thebluealliance.com.
Save the authorization key in a file called auth.py, which should be
importable as auth. For example:
```python
# Contents of auth.py
tba_key = 'thisisafakeblueallianceapikey'
```

The TBA API returns information as a JSON string. These functions use
the Python Standard Library's JSON module to convert the string to
a Python dictionary or list, depending on the structure of the JSON text.

Stacy Irwin, 7 Aug 2021
"""

import json
import urllib.request

import pandas as pd

import zebra.auth

BASE_URL = 'https://www.thebluealliance.com/api/v3'

def _send_request(path):
    """Sends HTTP request to The Blue Alliance Read API (V3).
    """
    full_url = BASE_URL + path
    http_headers = {
        'X-TBA-Auth-Key': zebra.auth.tba_key,
        'User-Agent': 'Zebra Model'
    }
    req = urllib.request.Request(full_url, headers=http_headers)
    url = ''
    with urllib.request.urlopen(req) as resp:
        if resp.status == 200:
            json_response = json.loads(resp.read())
    return json_response


def get_status():
    """Returns status of TBA Read API."""
    return _send_request('/status')


def get_districts(year, df=False):
    """Gets list of FRC Districts."""
    districts = _send_request(f'/districts/{year}')
    if df:
        districts = pd.DataFrame(districts)
    return districts


def get_events(key, option='full', df=False):
    """Gets all FRC events for a given year or district."""
    options = {'full':   '',
               'simple': '/simple',
               'keys':   '/keys'}
    if option.lower() not in options.keys():
        err_msg = "Data arg must be one of ['full', 'simple', 'keys']"
        raise ValueError(err_msg)
    if str(key).isnumeric():
        events = _send_request(f'/events/{key}{options[option]}')
    else:
        options = {'full':   '/events',
                   'simple': '/events/simple',
                   'keys':   '/events/keys'}
        events = _send_request(f'/district/{key}{options[option]}')
    if df:
        events = pd.DataFrame(events)
    return events




def get_match_keys(event_key):
    """Gets all match keys for a given event."""
    matches = _send_request(f'/event/{event_key}/matches/keys')
    return matches


def get_zebra(match_key):
    """Gets Zebra position tracking data for a given match."""
    zebra = _send_request(f'/match/{match_key}/zebra_motionworks')
    return zebra

def get_match_scores(match_key):
    """Gets detailed scores for a given match."""
    match = _send_request(f'/match/{match_key}')
    return match

        