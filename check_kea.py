#!/usr/bin/env python3

# Check the answer of a DHCPINFORM request on a KEA DHCP Server
# KEA might be running as a cluster but ONLY hot-standby supported
#
# I wrote this to use it as a Nagios plugin in CheckMK but decided against it,
# because scapy would need elevated privileges to grab the DHCP answer packet 
# AND I would have needed to install scapy within CheckMK and all these nasty things.
#
# So this check is divided in two parts:
# - This part runs scheduled every 5 minutes and writes its output to a state file
# - The second part is a simple bash script in the Nagios plugin directory
#   See check_kea.sh, same repo
# 
# Concerning KEA API security:
# ----------------------------
# Http requests on port 8000 are used by a KEA cluster to exhange state information
# and issue commands. Up to now, the security measure mentioned in the docs is encrypting the connections. 
#
# If you run KEA in a production environment, you should make sure, that your cluster members
# are in the same subnet and access is restricted by a local firewall and connctions are tls encrypted. 

# Sample nftables rules:
# 
#     chain input {
#        type filter hook input priority 0; policy accept;
#        ip saddr { primary_member, secondary_member, monitoring_host } tcp dport 8000 accept
#        iif lo tcp dport 8000 accept
#        tcp dport 8000 drop
#    }
#
# In this example, plantext http is used, which is okay (for me) because it's a dedicated network protected by firewalls 
# 
# dj0Nz Feb 2026

import sys, time, ipaddress, requests, json
from scapy.all import *

# Convert MAC address (needed to construct DHCPINFORM packet)
def mac_to_bytes(mac_addr: str) -> bytes:
    return int(mac_addr.replace(":", ""), 16).to_bytes(6, "big")

# Check is IP address is valid
def is_ipv4(input_address):
    try:
        valid_addr = ipaddress.IPv4Address(input_address)
        return True
    except:
        return False

# Process DHCP answer strucure and return server_id
def get_dhcp_server_id(pkt):
    if not pkt.haslayer(DHCP):
        return
    options = pkt[DHCP].options
    for opt in options:
        if isinstance(opt, tuple):
            key = opt[0]
            value = opt[1]
            if key == 'server_id':
                server_id = value
    return(server_id)

# Check if HA mode is hot-standby and server is primary
def check_kea_ha(kea_server):
    url = 'http://' + kea_server + ':8000'
    header_data = { 'Content-Type' : 'application/json' }
    payload = { "command": "status-get", "service": [ "dhcp4" ] }
    response = requests.post(url, data=json.dumps(payload), headers=header_data)
    status = response.status_code
    if not status == 200:
        return('Invalid API url')
    else:
        raw = response.json()
        ha_info = raw[0]['arguments'].get('high-availability')
        if ha_info:
            mode = raw[0]['arguments']['high-availability'][0]['ha-mode']
            if mode == 'hot-standby':
                role = raw[0]['arguments']['high-availability'][0]['ha-servers']['local']['role']
                return(role)
            else:
                return('Mode not hot-standby')
        # No HA so this is always the primary
        else:
            return('primary')

def main():

    try:
        server_ip = sys.argv[1]
    except:
        print(f"CRITICAL - Command line arguments missing")
        sys.exit(2)

    # Get interface name from default route and set timeout
    interface = conf.route.route("0.0.0.0")[0]
    timeout_sec = 3

    # Don't trust user input ;)
    if not is_ipv4(server_ip):
        print(f"CRITICAL - IP address parser failed")
        sys.exit(2)

    primary = check_kea_ha(server_ip)
    if not primary == 'primary':
        print(f"CRITICAL - HA mode is not primary")
        sys.exit(2)

    try:
        my_ip = get_if_addr(interface)
        my_mac = get_if_hwaddr(interface)

        # Assemble DHCPINFORM packet
        packet = (Ether(dst="ff:ff:ff:ff:ff:ff") /
               IP(src=my_ip, dst=server_ip) /
               UDP(sport=68, dport=67) /
               BOOTP(chaddr=mac_to_bytes(my_mac), ciaddr=my_ip) /
               DHCP(options=[("message-type", "inform"), "end"]))

        start_time = time.time()

        # Use srp to listen for return packets
        ans, unans = srp(packet, iface=interface, timeout=timeout_sec, verbose=False)

        duration = time.time() - start_time

        if ans:
            reply = ans[0][1]
            # If server_id does not match server_ip, the answer packet must be kaputt
            if get_dhcp_server_id(reply) == server_ip:
                print(f"OK - DHCP Response from {server_ip} in {duration:.2f}s | time={duration:.4f}s")
                sys.exit(0)
            else:
                print(f"CRITICAL - DHCP Server ID does not match input")
                sys.exit(2)
        else:
            print(f"CRITICAL - No DHCPACK received from {server_ip} within {timeout_sec}s")
            sys.exit(2)

    except Exception as e:
        print(f"UNKNOWN - Script error: {str(e)}")
        sys.exit(3)

if __name__ == "__main__":
    main()
