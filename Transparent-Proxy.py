#!/usr/bin/env python

import os
import sys
import logging
from scapy.all import *
from netfilterqueue import NetfilterQueue

# Configuration
LOG_FILE = "packet_log.txt"

# Set up logging
logging.basicConfig(level=logging.INFO, filename=LOG_FILE, filemode="a", format="%(asctime)s - %(levelname)s: %(message)s")

# Function to handle intercepted packets
def packet_handler(packet):
    try:
        pkt = IP(packet.get_payload())  # Convert packet payload to Scapy packet

        # Log the packet
        logging.info(f"Packet: {pkt.summary()}")

        # Modify the packet (example: change the destination IP to 8.8.8.8)
        pkt[IP].dst = "8.8.8.8"

        # Update checksums
        del pkt[IP].chksum
        del pkt[TCP].chksum
        del pkt[UDP].chksum

        packet.set_payload(bytes(pkt))  # Convert the modified Scapy packet back to bytes

    except Exception as e:
        logging.error(f"Error handling packet: {e}")

    packet.accept()  # Accept the packet (forward it)

def main():
    # Check for root privileges
    if os.geteuid() != 0:
        print("This script requires root privileges. Please run it as root.")
        sys.exit(1)

    # Enable IP forwarding to act as a proxy
    os.system("echo 1 > /proc/sys/net/ipv4/ip_forward")

    # Create a NetfilterQueue object and bind it to the queue number
    nfqueue = NetfilterQueue()
    nfqueue.bind(1, packet_handler)

    try:
        print("Proxy server started. Press Ctrl+C to stop.")
        nfqueue.run()

    except KeyboardInterrupt:
        print("\nProxy server stopped.")
        nfqueue.unbind()

if __name__ == "__main__":
    main()
