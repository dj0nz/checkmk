### CheckMK - local checks and plugins
Checkmk plugins and related stuff.

#### [check_debian_version.sh](check_debian_version.sh)
Local check which runs on a Debian system and checks if OS version is "current".

#### [check-netgear-version.py](check-netgear-version.py)
Checkmk plugin to check OS version on a Netgear NAS using snmp and compare to the latest version available at Netgear support website.

#### [check_kea.py](check_kea.py)
Python script that issues an INFORM request to a given KEA DHCP server. Can't be used as plugin directly, but...

#### [check_routeros_version.py](check_routeros_version.py)
Nagios plugin to check current version and pending updates on a Mikrotik RouterOS device

#### [backbox-backup-status.sh](backbox-backup-status.sh)
Local check for checking backup status on a Backbox Server

#### [nc-ver-check.sh](nc-ver-check.sh)
Script to check if latest Nextcloud version is installed locally. Output goes to state file which is read and interpreted by a local CheckMK check.





