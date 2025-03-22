#!/usr/bin/env python3

# Nagios Check Plugin for CheckMK: Mikrotik RouterOS Version
# 
# Copy to /omd/sites/$OMD_SITE/local/lib/nagios/plugins
# Activate in Other Services -> Nagios Plugins
# 
# dj0Nz Mar 2025

import os, requests, json, netrc, re, sys, socket

# next two lines needed to suppress warnings if self signed certificates are used
# from urllib3.exceptions import InsecureRequestWarning
# requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

site = os.environ['OMD_SITE']
auth_file = '/omd/sites/' + site + '/.netrc'

# check if port open
def port_open(ip,port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(1)
        sock.connect((ip, int(port)))
        return True
    except:
        return False

# api_call function returns json
def api_call(dest, command):
    url = 'https://' + dest + '/rest/' + command
    request_headers = {'Content-Type' : 'application/json'}
    r = requests.post(url, headers=request_headers, verify = False)
    status_code = r.status_code
    return [status_code, r.json()]

# check credentials file
exists = os.path.isfile(auth_file)
if not exists:
    print('Credentials file not found. Exiting.')
    exit(2)

# check input
try:
    input = sys.argv[1]
except IndexError:
    print('No input.')
    exit(2)

# check if reachable
if not port_open(input,443):
    print('Destination unreachable')
    exit(2)

# main section
command = 'system/package/update/check-for-updates'
response = api_call(input,command)
resp_code = str(response[0])
# interesting part is in second entry
data = response[1][1]
if resp_code == '200':
    status = data['status']
    already = re.findall('already', status)
    try:
        latest = data['latest-version']
    except:
        print('Unknown api call response format')
        exit(2)
    if already:
        print('System is up to date (' + str(latest) + ')')
        exitcode = 0
    else:
        print('Update available (' + str(latest) + ')')
        exitcode = 1
else:
    print('Api call not successful')
    exitcode = 2

exit(exitcode)
