#!/usr/bin/python3

# CheckMK API: List all debian hosts
# Output can be used as Ansible inventory
#
# Input needed:
# - Hostname or IP address of CheckMK server
# - CheckMK site name
# - Auth file name. Auth file is in .netrc format, but beware: Bearer auth does not work as expected if a file named ".netrc" is present.
#   Solution: Just give it an other name. ;)
#
# dj0Nz Jun 2025

import os, requests, json, netrc

# Vars needed: CheckMK Server hostname, site name, auth file name
host = 'cmk-host'
site = 'site-name'
auth_file = 'auth-file'

# Construct base url from hostname and site
url_prefix='http://' + host + '/' + site + '/check_mk/api/1.0/'

# There is no suitable "list hosts in folder, recursively" function,
# so we get a list of folders first and iterate through it to get hosts.
query_folder = '~debian'

# check credentials file, quit if not there
exists = os.path.isfile(auth_file)
if not exists:
    quit('Credentials file not found. Exiting.')

# get login credentials from .netrc file, token[0] contains user, token[2] the password
# See netrc module documentation at https://docs.python.org/3/library/netrc.html
auth = netrc.netrc(auth_file)
token = auth.authenticators(host)
if token:
    user = token[0]
    password = token[2]
    auth_bearer = 'Bearer ' + user + ' ' + password
else:
    quit('Host not found in netrc file. Exiting.')

# Set auth header
header_data = { 'Authorization' : auth_bearer, 'Accept' : 'application/json' }

# Collect all folders in query folder, recursive
api_command = 'domain-types/folder_config/collections/all?parent=' + query_folder
api_param = '&recursive=true'
url = url_prefix + api_command + api_param

# Do the request, store data in 'response'
response = requests.get(url,headers=header_data)
status = response.status_code

# Add folders to list
if status == 200:
    folders = []
    raw_json = response.json()['value']
    for item in raw_json:
        folders.append(item['id'])
else:
    print('Error. Code: ' + str(status))
    exit(1)

# Iterate through folders list and extract hosts in there
debian_hosts = []
for folder in folders:
    api_command = 'objects/folder_config/' + folder + '/collections/hosts'
    url = url_prefix + api_command
    response = requests.get(url,headers=header_data)
    status = response.status_code
    if status == 200:
        raw_json = response.json()['value']
        for item in raw_json:
            debian_hosts.append(item['id'])
    else:
        continue

debian_hosts.sort()

inventory = {
        "debian_vms": {
            "hosts": debian_hosts,
            "vars": {
                "ansible_user": "root"
            }
        },
        "_meta": {
            "hostvars": {}
        }
    }

print(json.dumps(inventory, indent=2))

