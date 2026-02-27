#!/bin/bash

# Nagios Plugin that reads check_kea.py output
# Copy to /omd/sites/$OMD_SITE/local/lib/nagios/plugins and chmod 700
# dj0Nz Feb 2026

CACHE_FILE="/var/run/kea.state"
MAX_AGE=900

if [[ -f $CACHE_FILE ]]; then
    FILE_AGE=$(($(date +%s) - $(stat -c %Y $CACHE_FILE)))
    if [[ $FILE_AGE -gt $MAX_AGE ]]; then
        echo "WARNING - Cache file older than 15 minutes"
        exit 1
    fi
    STATE=$(cat $CACHE_FILE | awk '{print $1}')
    if [[ $STATE == "OK" ]]; then
        EXIT_CODE=0
    else
        EXIT_CODE=2
    fi
    cat $CACHE_FILE
    exit $EXIT_CODE
else
    echo "UNKNOWN - Cache file not found"
    exit 3
fi
