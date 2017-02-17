"""Tests exercising the contactdb_api via HTTP.

TODO: Add code to setup a authed server for testing automatically.

Until we do not have an server automatically setup,
the functions in here must be run manually.
"""

import json
import os
from urllib.parse import urlencode
import urllib.error
import urllib.request

BASEURL='http://localhost:' + os.getenv('TESTPORT','8000')
ENDPOINT='/api/contactdb/org/manual/commit'

DATA_BAD=json.dumps({'spam': 1, 'eggs': 2, 'bacon': 0})
DATA=json.dumps({'commands': ['create'], 'orgs': [{'first_handle': None, 'ripe_org_hdl': 'ORG-BA202-RIPE', 'name': 'Bundesamt fuer Sicherheit in der Informationstechnik', 'contacts': [{'id': 2248, 'import_source': 'ripe', 'is_primary_contact': False, 'email': 'abuse@bund.de', 'tel': '+49 00000000001', 'import_time': '2017-01-23T09:43:12.672657', 'firstname': 'Abkus', 'comment': 'First command to a contact', 'role_type': 'abuse-c', 'format_id': 2, 'contact_id': 2691, 'openpgp_fpr': 'abcdef12', 'lastname': 'Abeler', 'organisation_id': 2458}], 'ti_handle': None, 'asns': [{'import_source': 'ripe', 'ripe_aut_num': None, 'number': 49234, 'import_time': '2017-01-23T09:43:12.672657', 'comment': '', 'asn_id': 49234, 'organisation_id': 2458, 'notification_interval': 0}], 'sector_id': None, 'comment': 'This is a second manual entry to test writing the details'}]})


def semi_automatic():
    # generic code for an Basic Auth connection
    password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(realm=None, uri=BASEURL,
                              user='intelmq', passwd='intelmq')
    auth_handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
    opener = urllib.request.build_opener(auth_handler)
    urllib.request.install_opener(opener)

    # generic code for a POST request
    request = urllib.request.Request(BASEURL + ENDPOINT)
    request.add_header("Content-Type", "application/json")
    f = urllib.request.urlopen(request, DATA.encode('utf-8'))

    # test1
    print(f.read().decode('utf-8'))

    # test2
    try:
        f = urllib.request.urlopen(request, DATA_BAD.encode('utf-8'))
    except urllib.error.HTTPError as err:
        print(err.code, err.reason)
        print(err.read().decode('utf-8'))

    # test3
    try:
        f = urllib.request.urlopen(request, 'not even json}'.encode('utf-8'))
    except urllib.error.HTTPError as err:
        print(err.code, err.reason)
        print(err.read().decode('utf-8'))


if __name__ == '__main__':
    semi_automatic()
