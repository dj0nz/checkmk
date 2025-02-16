#!/usr/bin/bash

# CheckMK Nagios plugin to check RouterOS version on a Mikrotik device.
#
# This script issues a command to query current version and available updates if any on a given Mikrotik
# RouterOS device using ssh with public key authentication. It returns "Ok" and the currently installed
# version if there are no pending updates and "Warning" in any other case.
# 
# Store to /omd/sites/$OMD_SITE/local/lib/nagios/plugins and chmod 700.
# See https://docs.checkmk.com/latest/en/active_checks.html for general information
#
# Preparation:
# ---
# I would recommend to create a dedicated user for that on the Mikrotik device and because it needs "full" access, I would
# also recommend to configure a strong password and restrict access to the CheckMK host address. To transfer the ssh 
# public key of the CheckMK site user to the device, you may use scp with the admin user.
#
# To be compatible with older RouterOS versions (for example the 6.49 version mentioned below), use RSA keys and 
# the "PubkeyAcceptedAlgorithms=+ssh-rsa" option in the command line.
# 
# Example: 
# scp .ssh/id_ed25519.pub admin@192.0.2.1:
# 
# Of course you have to be logged in on the command line of the CheckMK site you are using.
# After transferring the key, login to the router as admin and assign the key to the Monitoring user you created before
# 
# Example:
# /user ssh-keys import public-key-file=id_ed25519.pub user=mon
#
# I am using the user "mon" in this example but thats just a name.
# 
# The command to check the current version and available updates on a Mikrotik device is 'system package update check-for-updates' 
# and the complete output of that command would be:
#
#            channel: stable
#  installed-version: 6.49.17
#             status: finding out latest version...
#
#            channel: stable
#  installed-version: 6.49.17
#     latest-version: 6.49.17
#             status: System is already up to date
#
# We only need 'installed' and 'latest' from the last block.
# 
# To avoid querying too often (under "normal" circumstances, once a day is enough for an update check), the script stores this
# output to a temporary file, which is then used to query version information.
#
# That's it. Take care.
#
# djonz feb 2025

if [ "$#" -ne "1" ]; then
    echo ""
    echo "Usage: $0 HOSTNAME (or IP)"
    echo ""
    exit;
fi

# The user on the Mikrotik device
SSHUSER="mon"
WORKDIR=/omd/sites/$OMD_SITE/tmp
VERFORM='^[0-9]\.([0-9]|[1-9][0-9])\.([0-9]|[1-9][0-9])$'

# Check if file age is one day or less
FILECHECK=$(find $WORKDIR -name "$1.state" -mtime -1)
# ...and get a fresh update, if not.
if [[ $FILECHECK = "" ]]; then
    # Check if ssh connection possible
    if [[ $(timeout 3 bash -c "</dev/tcp/$1/22" 2>/dev/null &&  echo "Open" || echo "Closed") == "Open" ]]; then
        # Check if pubkey login possible
        # Add -o "PubkeyAcceptedAlgorithms=+ssh-rsa" if using older RouterOS versions.
        ssh -q -o PasswordAuthentication=no -o StrictHostKeyChecking=accept-new $SSHUSER@$1 exit
        # Try to grab version information, if the pubkey login check was successful
        if [ "$?" = "0" ]; then
            # Get last 5 lines of the 'system package update check-for-updates' command output.
            # For whatever reason, ssh outputs in dos-format (Line End = ^M). The 'tr' command takes care of that.
            ssh $SSHUSER@$1 'system package update check-for-updates' | tail -5 | tr -d '\r' > $WORKDIR/$1.state
        else
            echo "No pubkey login to router"
            exit 1
        fi
    else
        echo "No ssh connection to $1"
        exit 1
    fi
fi

# Get version numbers from local file
if [[ -f $WORKDIR/$1.state ]]; then
    INSTALLED=$(cat $WORKDIR/$1.state | grep installed | awk '{print $2}')
    LATEST=$(cat $WORKDIR/$1.state | grep latest | awk '{print $2}')
else
    echo "Missing state file"
fi

# Check if version string in correct format
if [[ ! $(echo $INSTALLED | grep -E $VERFORM) ]]; then
    echo "Unknown version format ($INSTALLED)"
    exit 1
else
    if [[ $INSTALLED = $LATEST ]]; then
        echo "Latest RouterOS Version installed ($LATEST)"
        exit 0
    else
        echo "RouterOS update $LATEST available (installed: $INSTALLED)"
        exit 1
    fi
fi
