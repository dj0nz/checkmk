### CheckMK - local checks and plugins
Checkmk plugins and related stuff.

#### [check_debian_version.sh](check_debian_version.sh)
Local check which runs on a Debian system and checks if OS version is "current".

#### [check-netgear-version.py](check-netgear-version.py)
**DEPRECATED** Checkmk plugin to check OS version on a Netgear NAS using snmp and compare to the latest version available at Netgear support website.

#### [check_kea.py](check_kea.py)
Python script that checks a given KEA DHCP server by issuing an DHCPINFORM request. Can't be used as plugin directly, but...

#### [check_kea.sh](check_kea.sh)
...the check_kea.sh is a Nagios plugin that reagds the check_kea.py output file and reports its status to CheckMK

#### [check_routeros_version.py](check_routeros_version.py)
Nagios plugin to check current version and pending updates on a Mikrotik RouterOS device

#### [backbox-backup-status.sh](backbox-backup-status.sh)
Local check for checking backup status on a Backbox Server

#### [nc-ver-check.sh](nc-ver-check.sh)
Script to check if latest Nextcloud version is installed locally. Output goes to state file which is read and interpreted by a local CheckMK check.

#### [cmk-agent-update.yaml](cmk-agent-update.yaml)
Ansible playbook to update CheckMK Agent on Debian hosts monitored by given CheckMK instance.  
Use with [get-cmk-debian.py](get-cmk-debian.py) as inventory script. 





