#!/bin/bash

# CheckMK: Prüfung auf Nextcloud Update
#
# Der Check ist zweigeteilt: Dieses Skript wird per Cron Job eingeplant und läuft 1-2 Mal am Tag.
# Die Ausgabe wandert in einem für CheckMK lesbaren Format in ein State File ($OUTPUT).
# Der Lokale Check für CheckMK in $CMK_AGENT/local liest einfach nur stumpf diese Datei aus:
#
# <local check>
# INPUT=/var/run/nc-update.state
# if [ -f $INPUT ]; then
#     cat $INPUT
# else
#     echo "2 \"Nextcloud Version\" - No state file."
# fi
# </local check>
#
# Dadurch muss nicht am Check Intervall in CheckMK gefummelt werden, sondern die Häufigkeit der
# Prüfungen auf neue Version wird rein über den Cron-Job gesteuert. Einmal am Tag völlig ausreichend.
#
# Praxistipp:
# Auf produktiven Systemen niemals eine "Nuller-Version" installieren. Auf eine xx.0.2 zu warten lohnt sich
# fast immer, es sei denn, eine neues Feature wird dringend benötigt.
#
# dj0Nz Feb 2026

# Nextcloud Versionen aus Github und local kratzen
NC_LATEST=$(/usr/bin/curl -SsL https://api.github.com/repos/nextcloud/server/releases/latest | jq -r '.tag_name' | tr -d v)
NC_LOCAL=$(sudo -u www-data php /var/www/nextcloud/occ status --output=json | jq -r .versionstring)

# Ausgabe umleiten. Sollte bei der Ausführung irgendein nicht angefangener Fehler auftreten,
# ist halt das Format der Ausgabedatei kaputt und CheckMK alarmiert was Blödes, was man dann repariert. ;)
OUTPUT=/var/run/nc-update.state
exec > $OUTPUT 2>&1

# Wenn da nicht die ueblichen Zahlen drin stehen: Fehler
if [[ ! $NC_LOCAL =~ ^[0-9]+\.[0-9]+\.[0-9]+$ || ! $NC_LATEST =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "2 \"Nextcloud Version\" - Unknown version format."
    exit 1
fi

# Wenn eine neue Version verfuegbar ist: Warning erzeugen
if [[ $NC_LATEST = $NC_LOCAL ]]; then
    echo "0 \"Nextcloud Version\" - Nextcloud is up to date (Version: $NC_LOCAL)"
else
    MV_REM=$(echo $NC_LATEST | awk -F '.' '{print $1}')
    MV_LOC=$(echo $NC_LOCAL | awk -F '.' '{print $1}')
    if [[ MV_REM -lt MV_LOC ]]; then
        echo "0 \"Nextcloud Version\" - Nextcloud locally on new major ($NC_LOCAL). Latest is $NC_LATEST."
    else
        echo "1 \"Nextcloud Version\" - Nextcloud update $NC_LATEST available. Currently installed: $NC_LOCAL."
    fi
fi
