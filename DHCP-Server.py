import os
import sys
import logging
from scapy.all import conf, DHCP, IP, UDP, BOOTP, send, sniff, wrpcap

# Enable IP forwarding (Make sure to run the script with admin/sudo privileges)
os.system("echo 1 > /proc/sys/net/ipv4/ip_forward")

# Configure logging
logging.basicConfig(filename="packet_log.txt", level=logging.INFO, format="%(asctime)s - %(message)s")

# Interface facing the internet (e.g., "eth0" on Linux)
INTERNET_INTERFACE = "YOUR_INTERNET_INTERFACE"

# Interface facing the device (e.g., "wlan0" on Linux)
DEVICE_INTERFACE = "YOUR_DEVICE_INTERFACE"

# DHCP server configuration
SERVER_IP = "192.168.1.1"
SUBNET_MASK = "255.255.255.0"
LEASE_TIME = 86400  # 24 hours lease time

# Define DHCP handling function
def handle_dhcp_packet(packet):
    if DHCP in packet and packet[DHCP].options[0][1] == 3:  # DHCP Request
        logging.info("Received DHCP Request from device")
        offer = create_dhcp_offer(packet)
        send(offer, iface=DEVICE_INTERFACE)
    elif DHCP in packet and packet[DHCP].options[0][1] == 1:  # DHCP Discover
        logging.info("Received DHCP Discover from device")
        offer = create_dhcp_offer(packet)
        send(offer, iface=DEVICE_INTERFACE)

# Create DHCP offer
def create_dhcp_offer(discover_packet):
    offer = (
        Ether(dst=discover_packet[Ether].src)
        / IP(src=SERVER_IP, dst="255.255.255.255")
        / UDP(dport=68, sport=67)
        / BOOTP(op=2, yiaddr=SERVER_IP, siaddr=SERVER_IP, chaddr=discover_packet[Ether].src)
        / DHCP(options=[("message-type", "offer"), ("server_id", SERVER_IP), ("subnet_mask", SUBNET_MASK), ("lease_time", LEASE_TIME), "end"])
    )
    return offer

# Function to handle packets between device and internet
def forward_packet(packet):
    logging.info("Forwarding packet")
    packet[IP].ttl -= 1  # Decrease the TTL to prevent infinite looping
    send(packet, iface=INTERNET_INTERFACE)

# Sniff and forward packets between device and internet
try:
    sniff(prn=handle_dhcp_packet, iface=DEVICE_INTERFACE, filter="udp and (port 67 or 68)", store=0)
except KeyboardInterrupt:
    sys.exit(0)
