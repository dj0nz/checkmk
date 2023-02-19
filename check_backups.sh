#!/bin/bash

# Skript prüft, ob für jeden Debian Host ein Backup existiert
# Läuft auf dem Backup-Server
# djonz Mar 2022

CURL=/usr/bin/curl
CMK_HOST=<CMK-HOST>
CMK_SITE=<CMK-SITE>
CMK_USER=<AUTOMATION USER>
CMK_SECRET=<AUTOMATION SECRET>
ACTION=get_all_hosts
BACKUP_DIR=/mnt/backup
NBL=""

# Liste Debian Hosts per Web API vom CHeck_MK holen
HOST_LIST=`$CURL -s "http://$CMK_HOST/$CMK_SITE/check_mk/webapi.py?action=$ACTION&_username=$CMK_USER&_secret=$CMK_SECRET&output_format=json" | jq '.result[] | select(.path | contains("debian")) | .hostname' | tr -d '"'`

for HOST in $HOST_LIST; do
    if [[ -d $BACKUP_DIR/$HOST ]]; then
        # Okay, wenn Backup File vorhanden und nicht zu alt
        OK=`find $BACKUP_DIR/$HOST -type f -mtime -8`
        if [[ $OK = "" ]]; then
            NBL+="$HOST "
        fi
    else
        NBL+="$HOST "
    fi
done

# Whitespace an Start und Ende entfernen
LIST=`echo $NBL | sed 's/^[[:blank:]]*//;s/[[:blank:]]*$//'`

if [[ $LIST = "" ]]; then
    echo "0 \"Debian Backups\" - Debian Backups vollständig"
else
    echo "1 \"Debian Backups\" - Kein Backup fuer: $LIST"
fi
