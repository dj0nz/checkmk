#!/bin/bash
#
# CheckMK local check for Debian
# Raise warning if installed update demands a reboot
# 
# dj0Nz Dec 2021

if [ -f /var/run/reboot-required ]; then
   REASON=`cat /var/run/reboot-required.pkgs`
   echo "1 \"Pending reboot\" - Reboot requested by package $REASON"
else
   echo "0 \"Pending reboot\" - No pending reboot."
fi
