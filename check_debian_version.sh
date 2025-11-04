#!/bin/bash

# CheckMK local check for Debian version
# Returns green if the version is current (stable or oldstable), yellow on oldoldstable (time to update!) and red in any other case
# dj0Nz Dec 2021

# extract version number, dist codename and dist branch from apt policy
readarray -d' ' -t RINFO <<< "$(apt-cache policy | grep -i debian | grep 'c=main' | egrep -iv 'update|security' | awk -F "," '{ print $1 " " $3 " " $4 }' | awk '{ print $2 " " $3 " " $4 }' | sed 's/[van]=//g')"

VERSION="${RINFO[0]}"
DISTR="${RINFO[1]}"
CODENAME=$(echo -e ${RINFO[2]})

# set state according to dist branch: 0=OK (stable/oldstable), 1=WARN (oldoldstable), 2=CRIT (all others)
case $DISTR in
   stable)
      RES=0
      ;;
   oldstable)
      RES=0
      ;;
   oldoldstable)
      RES=1
      ;;
   *)
      RES=2
      ;;
esac

# check script output. see https://docs.checkmk.com/latest/en/localchecks.html for info
echo "$RES \"Debian Version\" - Version: $VERSION ($CODENAME), Distribution: $DISTR"
