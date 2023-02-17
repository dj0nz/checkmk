#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
# Author: djonz[at]posteo[punkt]de
# URL   : https://github.com/dj0nz/checkmk
# Date  : 2023-02-17
#
# Monitor ReadyNAS OS version on a Netgear NAS
# Need the version as a single string in a file (outfile)
# Write outfile with get_readynas_version.py once a day or every other day

import sys
from cmk.base.plugins.agent_based.agent_based_api.v1 import *

outfile = '/tmp/readynas.version'

try:
    f = open(outfile, 'rb')
except OSError:
    latest = ""
else:
    with f:
        latest = f.readline()
        f.close

def discover_readynas_version(section):
    yield Service()

def check_readynas_version(section):
    if section == latest:
        yield Result(state=State.OK, summary="ReadyNAS OS is up to date")
    elif latest ==  "":
        yield Result(state=State.CRIT, summary="Unable to get online version. Check file/script.")
    else:
        yield Result(state=State.WARN, summary="ReadyNAS OS upgrade available")

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

