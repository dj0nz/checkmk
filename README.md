### CheckMK - local checks and plugins
Checkmk plugins and related stuff.

#### [check_backups.sh](check_backups.sh)
Local check which runs on a backup server, queries Checkmk for Debian hosts and checks if there is a more or less current backup file.

#### [check_debian_version.sh](check_debian_version.sh)
Local check which runs on a Debian system and checks if OS version is "current".

#### [reboot-required.sh](reboot-required.sh)
Local check that checks if a reboot is required after an upgrade.

#### [check-netgear-version.py](check-netgear-version.py)
Checkmk plugin to check OS version on a Netgear NAS using snmp and compare to the latest version available at Netgear support website.

