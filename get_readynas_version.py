#!/usr/bin/env python3

# Get current ReadyNAS OS version and write current version to outfile 
# This is needed by the check-netgear-version.py plugin. 
# Schedule to run once a day or every few days.
# dj0Nz Feb 2023

import requests
import re
import sys
from bs4 import BeautifulSoup

url = 'https://www.netgear.de/support/product/readynas_os_6.aspx#download'
outfile = '/tmp/readynas.version'

response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')
latest = soup.find('h1', string=re.compile('Softwareversion.*arm')).text.split()[1]

f = open(outfile, 'w')
f.write(latest + '\n')
f.close()
