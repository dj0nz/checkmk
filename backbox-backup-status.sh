#!/bin/bash
#
# CheckMK local check to get overall backup status from Backbox dashboard
#
# This script runs as local check on a Backbox server with installed CheckMK agent.
# It issues an API request on itself and returns "Ok" if all backups were successful.
# It will not run if token is abount to expire or file format is invalid.
# 
# Preparation:
# Add API token in Backbox server UI (Authentication -> API Token). Set API token lifetime
# according to your local API security guidelines (max. 180 days). Login to Backbox server, 
# elevate privileges, create token file ($TOKEN_FILE) in CheckMK agent home and chmod 600. 
# API token file format: <user>:<token>:<expires>, one per line. 
# Expires in epoch time, you may use https://www.epochconverter.com/ to calculate it from toke expiry date.
#
# Installation:
# Copy to /usr/lib/check_mk_agent/local/ and chmod 700.
#
# Product documentation:
# Backbox: https://support.backbox.com/s/documentation
# CheckMK: https://docs.checkmk.com/latest/en/index.html
#
# API documentation:
# https://<Backbox Server>/rest/data/swagger-ui.html
#
# dj0Nz Nov 2024

# The user used for issuing the API request
API_USER="mon"
#  The token file must be readable by CheckMK agent ONLY!
TOKEN_FILE="/var/lib/cmk-agent/.token"
# Reamining token lifetime - Issue warning and exit if token expires in less than $REMAIN days
REMAIN=7
END_DATE=$(($(date +%s)+86400*$REMAIN))

# Grab token from file
TOKEN=$(cat $TOKEN_FILE | grep $API_USER | cut -d ':' -f2)
EXPIRES=$(cat $TOKEN_FILE | grep $API_USER | cut -d ':' -f3)

# Check if the expire time is in valid format
if [[ $(date -d "@$EXPIRES" 2>&1 | grep invalid) ]]; then
    echo "2 \"Backbox Backups\" - Token expire time is invalid."
    exit 1
else
    # Check if token is about to expire
    if [[ $EXPIRES < $END_DATE ]]; then
        echo "1 \"Backbox Backups\" - Token expires $(date -d "@$EXPIRES"). Renew now!"
        exit 1
    fi
fi

# Backbox server to query
SERVER=192.0.2.1

# API command
COMMAND="dashboard/backupStatus"
# Initial Value for successful backups
SUCCESS=0

# Get json status
STATUS=$(curl -X GET -k --silent -H "Accept: application/json" -H "AUTH:$TOKEN" "https://$SERVER/rest/data/token/api/$COMMAND")

# Grab total and success from json
SUCCESS=$(echo $STATUS | jq '.[]|."successDevices"')
TOTAL=$(echo $STATUS | jq '.[]|."totalDevices"')

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
