#!/bin/bash
#
# check dhcpd answer
# 
# this is local check running on a linux dhcp server. it relies on a second host 
# (or the checkmk server) sending a dhcpdiscover message to the dhcp server and 
# copying a file containing the response back to the dhcp server.
#
# for the dhcpdiscover message to be sent, i use nmap. you may also use dhcping,
# but the output is ... hm ... okay it says "got answer" or not that's all. :-/
# 
# prerequisites: 
# - another linux host in the network where the dhcp server is listening 
#   for requests (can be the monitoring server itself)
# - ssh pubkey auth from this machine to the dhcp server
# - locally installed nmap on this machine
# - schedule a script cronjob (every 10 minutes or so) with the following commands:
#   nmap -sU -p67 --script dhcp-discover [dhcp server address] > /tmp/dhcp-check
#   scp -q /tmp/dhcp-check [dhcp server]:/tmp/dhcp-check
#
# links:
# - dhcpdiscover: https://www.freesoft.org/CIE/RFC/2131/23.htm
# - nmap scripts: https://nmap.org/book/nse-usage.html
# 
# djonz may 2022

FILE=/tmp/dhcp-check

# check if file there
if [[ -f $FILE ]]; then
   # check file age
   AGE=`find $FILE -mmin +30`
   if [[ $AGE ]]; then
      echo "1 \"DHCP Server Answer\" - Check file older than 30 min."
   else
      # check if answer contains a dhcpack message and echo result
      ANSWER=`cat $FILE | grep 'Message Type' | awk '{print $5}'`
      if [[ $ANSWER = "DHCPACK" ]]; then
         echo "0 \"DHCP Server Answer\" - DHCP server answer ok ($ANSWER)."
      else
         echo "1 \"DHCP Server Answer\" - DHCP server answer not ok ($ANSWER)."
      fi
   fi
else
   # raise alarm if check file not there
   echo "2 \"DHCP Server Answer\" - No DHCP server check file!"
fi