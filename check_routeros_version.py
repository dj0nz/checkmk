#!/usr/bin/env python3

# Nagios Check Plugin for CheckMK: Mikrotik RouterOS Version
#
# Copy to /omd/sites/$OMD_SITE/local/lib/nagios/plugins
# Activate in Other Services -> Nagios Plugins
# Adjust check interval to anything other than the default 60 seconds (> 300 sec)
#
# How it works:
# This script uses the check-for-updates api call to get the latest RouterOS version
# available for a given Mikrotik device together with the version currently installed.
# Api call results are cached to a state file and calls are only issued if state file
# ttl expired. See VARS section below.
#
# Dependencies: To authenticate the requests, a netrc-format file is needed.
# See https://everything.curl.dev/usingcurl/netrc.html for format definition.
# The file does NOT have to be named .netrc, see auth_file below.
# Permissions must be 600 (owner read/write only), otherwise the netrc module
# will refuse to parse it.
#
# The API user must be defined on the router and DONT USE ADMIN. Unfortunately, a readonly user
# is not sufficient. Create a user group with read + write + policy + api + rest-api permissions, then add a
# dedicated api user to that group, restrict source address, set 1 minute inactivity timeout and inactivity policy to logout.
# The latter is needed because api users dont get logged off automatically after requests!
#
# dj0Nz [djonz@posteo.de] Mar 2025, revised Jul 2026
# License: https://unlicense.org/

import os, requests, json, netrc, re, sys, socket, time

# next two lines needed to suppress warnings if self signed certificates are used (or expired or missing SANs ;))
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# VARS
# auth_file: path to netrc-format credentials file, any file name works (default: $OMD_SITE/.netrc)
# cache_ttl: seconds a successful result is considered fresh (default: 86400 = 1 day)
# state_file_prefix: state file path and prefix, see state_file_path function for description
site = os.environ['OMD_SITE']
auth_file = '/omd/sites/' + site + '/.netrc'
state_file_prefix = '/tmp/check_routeros_version_'
cache_ttl = 86400

# check if port open
def port_open(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(2)
        sock.connect((ip, int(port)))
        return True
    except OSError:
        return False
    finally:
        sock.close()


# read login/password for dest from a netrc-format file.
# this replaces relying on requests' implicit netrc lookup, which only checks the
# NETRC environment variable or ~/.netrc / ~/_netrc and therefore silently fails to
# authenticate if the credentials file has any other name or location.
def get_credentials(path, dest):
    try:
        parsed = netrc.netrc(path)
    except (FileNotFoundError, netrc.NetrcParseError) as e:
        print('Credentials file error: ' + str(e))
        exit(2)
    entry = parsed.authenticators(dest)
    if entry is None:
        print('No credentials for ' + dest + ' found in ' + path)
        exit(2)
    login, _, password = entry
    return (login, password)


# api_call function returns [status_code, parsed_json_or_None, raw_text]
def api_call(dest, command, auth):
    url = 'https://' + dest + '/rest/' + command
    request_headers = {'Content-Type': 'application/json'}
    try:
        r = requests.post(url, headers=request_headers, auth=auth, verify=False, timeout=10)
    except requests.exceptions.Timeout:
        print('Api call timed out: Update servers unreachable')
        exit(1)
    except requests.exceptions.RequestException as e:
        print('Api call failed: ' + str(e))
        exit(2)
    try:
        payload = r.json()
    except ValueError:
        payload = None
    return [r.status_code, payload, r.text]

# --- daily cache, only used for successful (exitcode 0) results ---
# the api user has a short inactivity timeout with logout policy (see header comment), 
# so hitting the api on every check interval is unnecessary load. A failed run
# is never cached, so problems are still visible on the next check interval.
def state_file_path(dest):
    return state_file_prefix + site + '_' + dest + '.state'

def read_cache(dest):
    path = state_file_path(dest)
    if not os.path.isfile(path):
        return None
    try:
        with open(path) as f:
            state = json.load(f)
    except (ValueError, OSError):
        return None
    if time.time() - state.get('timestamp', 0) > cache_ttl:
        return None
    return state

def write_cache(dest, message, exitcode):
    path = state_file_path(dest)
    state = {'timestamp': time.time(), 'message': message, 'exitcode': exitcode}
    try:
        with open(path, 'w') as f:
            json.dump(state, f)
    except OSError as e:
        # caching is an optimization, not a hard requirement - dont fail the check because of it
        sys.stderr.write('Warning: could not write state file: ' + str(e) + '\n')

# check input
try:
    dest = sys.argv[1]
except IndexError:
    print('No input.')
    exit(2)

# serve cached result if still fresh
cached = read_cache(dest)
if cached:
    print(cached['message'] + ' (cached)')
    exit(cached['exitcode'])

# check credentials file
if not os.path.isfile(auth_file):
    print('Credentials file not found: ' + auth_file)
    exit(2)

credentials = get_credentials(auth_file, dest)

# check if reachable
if not port_open(dest, 443):
    print('Destination unreachable')
    exit(2)

# main section
command = 'system/package/update/check-for-updates'
resp_code, data, raw = api_call(dest, command, credentials)

if resp_code != 200:
    # on failure RouterOS returns a JSON object with error/message/detail fields
    # https://manual.mikrotik.com/docs/developer-guides/rest-api/
    detail = ''
    if isinstance(data, dict):
        detail = ' - ' + str(data.get('message', '')) + ': ' + str(data.get('detail', ''))
    print('Api call not successful (HTTP ' + str(resp_code) + ')' + detail)
    exit(2)

# RouterOS returns a single JSON object for this endpoint (see forum thread below)
# https://forum.mikrotik.com/t/rest-api-is-it-a-bug-solved/175081
if isinstance(data, list):
    data = data[-1] if data else {}

if not isinstance(data, dict) or 'status' not in data:
    print('Unknown api call response format: ' + raw[:200])
    exit(2)

status = data['status']
current = data.get('installed-version', 'unknown')
already = re.findall('already', status)

if already:
    # when already up to date, RouterOS does not include latest-version in the reply
    print('System is up to date (' + str(current) + ')')
    exitcode = 0
else:
    latest = data.get('latest-version')
    if latest:
        print('Update available (' + str(latest) + '), current: ' + str(current))
        exitcode = 1
    else:
        print('Status: ' + status + ' (current: ' + str(current) + ')')
        exitcode = 1

if exitcode == 0:
    write_cache(dest, 'System is up to date (' + str(current) + ')', exitcode)

exit(exitcode)
