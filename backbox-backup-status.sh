#!/bin/bash
#
# CheckMK local check to get overall backup status from Backbox dashboard
#
# This script runs as local check on a Backbox server with installed CheckMK agent.
# It issues an API request on itself and returns "Ok" if all backups were successful.
#
# Failure conditions covered:
# - Return warning if successDevices not equal totalDevices
# - Return error if 
#     - successDevices = 0 
#     - API request not successful
#     - Password file not found
# 
# Preparation (Backbox Web UI):
# - Create restricted user role with all permissions removed (Access to Dashboard/Status can't be removed)
# - Create API user and assign the restricted role, configure strong password (Diceware is your friend)
#
# Installation (via Secure Shell):
# - Copy script to /usr/lib/check_mk_agent/local/ and chmod 700
# - Create "hidden" password file in /var/lib/cmk-agent (see $PASSWORD_FILE below) and chmod 600
# - The password file should contain the API user's password only 
# - Wait for Service Discovery to detect the new check or discover manually
#
# Product documentation:
# Backbox: https://support.backbox.com/s/documentation
# CheckMK: https://docs.checkmk.com/latest/en/index.html
#
# Backbox API documentation:
# https://$BACKBOX/rest/data/swagger-ui.html
#
# dj0Nz Feb 2026

####
# Config section

# Backbox server to query
BACKBOX=192.0.2.21
# Output files
OUTPUT=/tmp/backup_status.json
HEADER=/tmp/header.txt
# API User
USERNAME="api"
# File containing API user's password
PASSWORD_FILE=/var/lib/cmk-agent/.apipw

# Config section end
####

# Get API password
if [[ -f $PASSWORD_FILE ]]; then
    PASSWORD=$(cat $PASSWORD_FILE)
else
    echo "2 \"Backbox Backups\" - Missing login credentials!"
    exit 1
fi

# Get API token: Issue login and store response header. Session token is in "AUTH"
curl -s -D $HEADER "https://$BACKBOX/rest/data/token/api/login?username={$USERNAME}&password={$PASSWORD}" -k -o /dev/null

# Check response header. Anything other than HTTP/1.1 200 OK in the first line is an error
RESPONSE=$(cat $HEADER | head -1 | awk '{print $2}')
if [[ ! "$RESPONSE" == "200" ]]; then
    echo "2 \"Backbox Backups\" - API login not successful (Http code: $RESPONSE)!"
    exit 1
fi

# Extract auth token from response header
TOKEN=$(cat $HEADER | grep AUTH | awk '{print $2}')
rm $HEADER

# Get json structure containing overall backup status
COMMAND="dashboard/backupStatus"
RESPONSE=$(curl -o $OUTPUT -w "%{http_code}\n" -X GET -k --silent -H "Accept: application/json" -H "AUTH:$TOKEN" "https://$BACKBOX/rest/data/token/api/$COMMAND")

if [[ ! "$RESPONSE" == "200" ]]; then
    echo "2 \"Backbox Backups\" - API request not successful (Http code: $RESPONSE)!"
    exit 1
fi

# Grab total and success from json
SUCCESS=$(jq '.[]|."successDevices"' $OUTPUT)
TOTAL=$(jq '.[]|."totalDevices"' $OUTPUT)

# Output section
if [[ $SUCCESS -eq 0 ]]; then
    echo "2 \"Backbox Backups\" - No successful backups at all!"
else
    if [[ $SUCCESS -eq $TOTAL ]]; then
        echo "0 \"Backbox Backups\" - All backups successful."
    else
        echo "1 \"Backbox Backups\" - Some backups failed - investigate!"
    fi
fi
