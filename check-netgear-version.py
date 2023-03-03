#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: The unlicense. See repo.
#
# Author : djonz[at]posteo[punkt]de
# URL    : https://github.com/dj0nz/checkmk
# Date   : 2023-03-01
# Version: 2.0
#
# Purpose: Monitor ReadyNAS OS version on a Netgear NAS
# 
# Install:
# - copy to /omd/sites/<site>/local/lib/python3/cmk/base/plugins/agent_based and chmod 700
#
# How it works:
# - Download the Netgear ReadyNAS OS software download page to a local file once a day (configurable)
# - Parse that file to get a list of ReadyNAS OS software versions
# - Determine current release (the first in the list)
# - Do an SNMP query on Netgear NAS devices to determine installed version
# - Raise warning if software is outdated
# - Error states should self-heal. If not, check Netgear support site contents
#
# Adjustable parameters:
# - You may adjust the numdays var in order to download the download page only once a week or so,
#   but, for runtime reasons, don't run it too often
# - If you're not from Germany you might want to adjust the download URL
# - The htmlfile could also be stored in /var/run or any other directory you like

import os
import re
import time
import requests
from html.parser import HTMLParser
from cmk.base.plugins.agent_based.agent_based_api.v1 import *

# URL of the Netgear (Germany) ReadyNAS OS download page
url = 'https://www.netgear.de/support/product/readynas_os_6.aspx#download'

# Regex for identifying Netgear ReadyNAS OS support site
site_identifier='<title.*?>(ReadyNAS.+?)</title>'

# The file that holds the downloaded HTML code from the Netgear Support Website
# Gets refreshed automatically after $numdays days. See "Create htmlfile" section
htmlfile = '/tmp/netgear-support.html'

# Current time needed to determine htmlfile age
current_time = time.time()

# One day in seconds, needed for file age calculation
daysec = 86400

# File age in days. If html file is older, it gets deleted and downloaded on next run. 
numdays = 1

# Class to extract list of versions (with current version = first entry) from Netgear Germany download site
# Thanks to Robin David (https://gist.github.com/RobinDavid/9196709) for the class logic
class versions_list(HTMLParser):
    head = False
    version = list()
    def handle_starttag(self, tag, attrs):
        if tag == 'h1':
            self.head = True
    def handle_data(self, data):
        if self.head:
            if data.startswith('Softwareversion'):
                # You may also check platform (x86/arm), which is in [2]
                self.version.append(data.split()[1])
    def handle_endtag(self, tag):
        if tag =='h1':
            self.head = False

# Create htmlfile if it isn't there any more
if not os.path.isfile(htmlfile):
    response = requests.get(url)
    with open(htmlfile, 'w') as file:
        file.write(response.text)
        file.close()

# Open existing file and extract html
try:
    file = open(htmlfile, 'r')
except OSError:
    latest = ""
else:
    with file:
        html = file.read()
        file.close()
    # Check if html contains expected Netgear contents
    pattern=re.compile(site_identifier)
    titles=re.findall(pattern,html)
    # Only run parser if it's a ReadyNAS page
    if titles:
        # Parse current version (first list entry) from htmlfile
        readaynas_versions = versions_list()
        readaynas_versions.feed(html)
        if readaynas_versions.version:
            latest = readaynas_versions.version[0]
            # Basic syntax checking: We're expecting a specific format...
            check = re.match('^\d{1,2}\.\d{1,2}\.\d{1,2}$', latest)
            if not check:
                latest = ""
                os.remove(htmlfile)
            # Delete htmlfile if it's older than numdays
            if os.path.isfile(htmlfile):
                file_time = os.stat(htmlfile).st_mtime
                if(file_time < current_time -daysec*numdays):
                    os.remove(htmlfile)
        else:
            latest = ""
            os.remove(htmlfile)
    else:
        latest = ""
        os.remove(htmlfile)

# Service discovery function
def discover_readynas_version(section):
    yield Service()

# Check logic and output
def check_readynas_version(section):
    current = section[0][0]
    if current == latest:
        yield Result(state=State.OK, summary="ReadyNAS OS is up to date")
    elif latest ==  "":
        yield Result(state=State.CRIT, summary="Unable to get online version.")
    else:
        yield Result(state=State.WARN, summary="ReadyNAS OS upgrade available")

# Register section. Only activate plugin on ReadyNAS devices, query current version only
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

# Plugin registration
register.check_plugin(
    name = "readynas_version",
    service_name="ReadyNAS OS Version",
    discovery_function=discover_readynas_version,
    check_function=check_readynas_version
)
