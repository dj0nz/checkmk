#!/bin/bash
#
# CheckMK local check to get overall backup status from Backbox dashboard
#
# This script runs as local check on a Backbox server with installed CheckMK agent.
# It issues an API request on itself and returns "Ok" if all backups were successful.
#
# Failure conditions covered:
# - Warning if successDevices != totalDevices
# - Warning if no devices configured (totalDevices = 0)
# - Critical if successDevices = 0 with devices present
# - Critical on API errors, missing password file, or unparseable response
#
# Preparation (Backbox Web UI):
# - Create restricted user role with all permissions removed (Dashboard/Status remains)
# - Create API user, assign the restricted role, set a strong password
#
# Installation (via Secure Shell):
# - Copy script to /usr/lib/check_mk_agent/local/ and chmod 700
# - Create password file in /var/lib/cmk-agent (see PASSWORD_FILE below), chmod 600
# - Password file contains the API user's password only
# - Wait for Service Discovery to detect the new check or discover manually
#
# Product documentation:
# Backbox: https://support.backbox.com/s/documentation
# CheckMK: https://docs.checkmk.com/latest/en/index.html
#
# Backbox API documentation:
# https://$BACKBOX/rest/data/swagger-ui.html
#
# Note: This script uses Backbox' Internal API which is deprecated by the
# vendor. Reachitecture required once the replacement API is published.
#
# dj0Nz Feb 2026
# Revised Jul 2026
####

# Config section
BACKBOX=192.0.2.21
USERNAME="api"
PASSWORD_FILE=/var/lib/cmk-agent/.apipw
SERVICE='"Backbox Backups"'
CURL_TIMEOUT=10
# Config section end
####

# Use mktemp; ensure cleanup on every exit path (header file briefly holds AUTH token)
HEADER=$(mktemp) || { echo "2 $SERVICE - Cannot create temp file"; exit 1; }
OUTPUT=$(mktemp) || { echo "2 $SERVICE - Cannot create temp file"; exit 1; }
trap 'rm -f "$HEADER" "$OUTPUT"' EXIT

# Read API password, strip trailing newline if present
if [[ ! -r "$PASSWORD_FILE" ]]; then
    echo "2 $SERVICE - Missing or unreadable login credentials!"
    exit 1
fi
PASSWORD=$(<"$PASSWORD_FILE")
PASSWORD="${PASSWORD%$'\n'}"

# Login: get HTTP status via -w, store headers (AUTH token is in there)
LOGIN_CODE=$(curl -s -k --max-time "$CURL_TIMEOUT" -D "$HEADER" -o /dev/null -w '%{http_code}' \
    "https://$BACKBOX/rest/data/token/api/login?username=${USERNAME}&password=${PASSWORD}")

if [[ "$LOGIN_CODE" != "200" ]]; then
    echo "2 $SERVICE - API login not successful (HTTP code: $LOGIN_CODE)!"
    exit 1
fi

# Extract auth token, strip CR that comes with HTTP headers
TOKEN=$(awk '/^AUTH:/ {print $2; exit}' "$HEADER" | tr -d '\r')
if [[ -z "$TOKEN" ]]; then
    echo "2 $SERVICE - Could not extract auth token"
    exit 1
fi

# Fetch backup status
COMMAND="dashboard/backupStatus"
API_CODE=$(curl -s -k --max-time "$CURL_TIMEOUT" -o "$OUTPUT" -w '%{http_code}' \
    -X GET -H "Accept: application/json" -H "AUTH:$TOKEN" \
    "https://$BACKBOX/rest/data/token/api/$COMMAND")

if [[ "$API_CODE" != "200" ]]; then
    echo "2 $SERVICE - API request not successful (HTTP code: $API_CODE)!"
    exit 1
fi

# Extract both values in a single jq call; validate before arithmetic
read -r SUCCESS TOTAL < <(jq -r '.[] | "\(.successDevices) \(.totalDevices)"' "$OUTPUT" 2>/dev/null)
if [[ ! "$SUCCESS" =~ ^[0-9]+$ ]] || [[ ! "$TOTAL" =~ ^[0-9]+$ ]]; then
    echo "2 $SERVICE - Unexpected API response (cannot parse success/total)"
    exit 1
fi

# Output section
if [[ $TOTAL -eq 0 ]]; then
    echo "1 $SERVICE - No backup devices configured"
elif [[ $SUCCESS -eq 0 ]]; then
    echo "2 $SERVICE - No successful backups at all ($SUCCESS/$TOTAL)!"
elif [[ $SUCCESS -eq $TOTAL ]]; then
    echo "0 $SERVICE - All $TOTAL backups successful"
else
    echo "1 $SERVICE - $((TOTAL-SUCCESS)) of $TOTAL backups failed - investigate!"
fi
