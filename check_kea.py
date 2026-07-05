#!/usr/bin/env python3

# Check the answer of a DHCPINFORM request on a KEA DHCP Server
# KEA might be running as a cluster but ONLY hot-standby supported
#
# I wrote this to use it as a Nagios plugin in CheckMK but decided against it,
# because scapy would need elevated privileges to grab the DHCP answer packet 
# AND I would have needed to install scapy within CheckMK and all these nasty things.
#
# So this check is divided in two parts:
# - This part runs scheduled (every 5 minutes in this example) and writes its output 
#   to a state file and to a log file for post-mortem analysis
#   crontab: */5 * * * * /usr/local/bin/check_kea_dhcp.py [dhcp.ser.ver.ip] >/dev/null 2>&1
# - The second part is a simple bash script in the Nagios plugin directory
#   See check_kea.sh, same repo
# 
# Concerning KEA API security:
# ----------------------------
# Http requests on port 8000 are used by a KEA cluster to exhange state information
# and issue commands. Up to now, the security measure mentioned in the docs is "encrypting the connections". :-/ 
#
# If you run KEA in a production environment, you should make sure, that your cluster members
# are in the same subnet and access is restricted by a local firewall and connctions are tls encrypted. 
#
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
# Patched Jul 2026: API timeout/exception handling, logging, atomic state write, exclusive run lock

import sys, time, ipaddress, requests, json, os, tempfile, logging, fcntl
from scapy.all import *

STATE_FILE = "/var/run/kea.state"
LOG_FILE = "/var/log/check_kea.log"
LOCK_FILE = "/var/run/kea_check.lock"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# Acquire an exclusive, non-blocking lock so overlapping cron runs
# (e.g. after a hang) can't write to the state file concurrently.
# Returns the open file handle (keep it alive) or None if already locked.
def acquire_lock():
    lock_fp = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return None
    return lock_fp

# Write to a temp file in the same directory, then atomically rename.
# Readers of STATE_FILE never see a partial or empty file.
def write_state(content):
    dir_name = os.path.dirname(STATE_FILE)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix=".kea_state_")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content + "\n")
        os.chmod(tmp_path, 0o644)
        os.replace(tmp_path, STATE_FILE)
    except Exception:
        os.unlink(tmp_path)
        raise

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
        return None
    server_id = None
    options = pkt[DHCP].options
    for opt in options:
        if isinstance(opt, tuple):
            key = opt[0]
            value = opt[1]
            if key == 'server_id':
                server_id = value
    return(server_id)

# Check if HA mode is hot-standby and server is primary
def check_kea_ha(kea_server, api_timeout):
    url = 'http://' + kea_server + ':8000'
    header_data = { 'Content-Type' : 'application/json' }
    payload = { "command": "status-get", "service": [ "dhcp4" ] }
    try:
        response = requests.post(url, data=json.dumps(payload), headers=header_data, timeout=api_timeout)
    except requests.exceptions.RequestException as e:
        logging.warning(f"check_kea_ha: control agent unreachable: {e}")
        return(f"API unreachable: {e}")
    status = response.status_code
    if not status == 200:
        return('Invalid API url')
    try:
        raw = response.json()
        ha_info = raw[0]['arguments'].get('high-availability')
    except (ValueError, KeyError, IndexError) as e:
        logging.warning(f"check_kea_ha: malformed API response: {e}")
        return(f"Malformed API response: {e}")
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

    lock = acquire_lock()
    if lock is None:
        # Previous run still active, don't touch the state file, keep last valid state
        logging.warning("previous run still active, skipping this cycle")
        sys.exit(3)

    try:
        server_ip = sys.argv[1]
    except:
        result = "CRITICAL - Command line arguments missing"
        logging.error(result)
        print(result)
        sys.exit(2)

    # Get interface name from default route and set timeout
    interface = conf.route.route("0.0.0.0")[0]
    timeout_sec = 3

    # Don't trust user input ;)
    if not is_ipv4(server_ip):
        result = "CRITICAL - IP address parser failed"
        logging.error(result)
        write_state(result)
        print(result)
        sys.exit(2)

    primary = check_kea_ha(server_ip, timeout_sec)
    if not primary == 'primary':
        result = f"CRITICAL - HA mode is not primary ({primary})"
        logging.error(result)
        write_state(result)
        print(result)
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
        logging.info(f"srp result: answered={len(ans)} unanswered={len(unans)} duration={duration:.2f}s")

        if ans:
            reply = ans[0][1]
            # If server_id does not match server_ip, the answer packet must be kaputt
            if get_dhcp_server_id(reply) == server_ip:
                result = f"OK - DHCP Response from {server_ip} in {duration:.2f}s | time={duration:.4f}s"
                logging.info(result)
                write_state(result)
                print(result)
                sys.exit(0)
            else:
                result = "CRITICAL - DHCP Server ID does not match input"
                logging.error(result)
                write_state(result)
                print(result)
                sys.exit(2)
        else:
            result = f"CRITICAL - No DHCPACK received from {server_ip} within {timeout_sec}s"
            logging.error(result)
            write_state(result)
            print(result)
            sys.exit(2)

    except Exception as e:
        result = f"UNKNOWN - Script error: {str(e)}"
        logging.error(result)
        write_state(result)
        print(result)
        sys.exit(3)

if __name__ == "__main__":
    main()