#!/bin/bash

# CheckMK local check for Debian version
# dj0Nz Dec 2021

# extract version number, dist codename and dist branch from apt policy
readarray -d' ' -t RINFO <<< "$(apt-cache policy | grep -i debian | grep 'c=main' | egrep -iv 'update|security' | awk -F "," '{ print $1 " " $3 " " $4 }' | awk '{ print $2 " " $3 " " $4 }' | sed 's/[van]=//g')"

VERSION="${RINFO[0]}"
DISTR="${RINFO[1]}"
CODENAME=`echo -e ${RINFO[2]}`

# set state according to dist branch: 0=OK (stable), 1=WARN (oldstable), 2=CRIT (all others)
case $DISTR in
   stable)
      RES=0
      ;;
   oldstable)
      RES=1
      ;;
   *)
      RES=2
      ;;
esac

# check script output. see https://docs.checkmk.com/latest/en/localchecks.html for info
echo "$RES \"Debian Version\" - Version: $VERSION ($CODENAME), Distribution: $DISTR"
