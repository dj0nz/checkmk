#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
# Author: djonz[at]posteo[punkt]de
# URL   : https://github.com/dj0nz/checkmk
# Date  : 2023-02-17
#
# CheckMK plugin to monitor ReadyNAS OS version on a Netgear NAS
# Needs the current version grabbed from https://www.netgear.de/support/product/readynas_os_6.aspx#download
# as a single string in a local file (versionfile).
# Write versionfile with get_readynas_version.py (or any other script) once a day or every few days
# Guidelines used: https://docs.checkmk.com/latest/en/devel_check_plugins.html

from cmk.base.plugins.agent_based.agent_based_api.v1 import *

# See repo for example script to extract version from netgear download site
versionfile = '/tmp/readynas.version'

# handle file not found or any other os level error
try:
    f = open(versionfile, 'r')
except OSError:
    latest = ""
else:
    with f:
        latest = f.readline()
        f.close
        # remove crlf if present
        latest = latest.replace('\n', '')

def discover_readynas_version(section):
    yield Service()

def check_readynas_version(section):
    current = section[0][0]
    if current == latest:
        yield Result(state=State.OK, summary="ReadyNAS OS is up to date")
    elif latest ==  "":
        yield Result(state=State.CRIT, summary="Unable to get online version. Check file/script.")
    else:
        yield Result(state=State.WARN, summary="ReadyNAS OS upgrade available")

# Only query current ReadyNAS OS version
register.snmp_section(
    name = "readynas_version",
    detect = startswith(".1.3.6.1.2.1.1.1.0", "ReadyNAS"),
    fetch = SNMPTree(
        base = '.1.3.6.1.4.1.4526.22',
        oids = [
            '1.0',
        ],
    ),
)

register.check_plugin(
    name = "readynas_version",
    service_name="ReadyNAS OS Version",
    discovery_function=discover_readynas_version,
    check_function=check_readynas_version
)

