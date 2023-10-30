import dns.message
import dns.query
import dns.rcode
import dns.resolver
import socketserver
import threading
import datetime

# DNS server settings
LISTEN_ADDRESS = '0.0.0.0'  # Address to listen on (all network interfaces)
LISTEN_PORT = 53  # Port to listen on
UPSTREAM_DNS = '8.8.8.8'  # Upstream DNS server to forward valid requests

# Blacklisted domains
BLACKLIST = ['youtube', 'youtubekids', 'youtubei']

# Whitelisted IP addresses
WHITELIST = ['192.168.1.2', '192.168.1.3']

# Block period (from 4PM to 8AM next day)
BLOCK_START_TIME = datetime.time(13, 0)  # 1:00 PM
BLOCK_END_TIME = datetime.time(8, 0)   # 8:00 AM

def log_request(domain, ip):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp} - Domain: {domain}, IP: {ip}\n"
    with open("dns_log.txt", "a") as log_file:
        log_file.write(log_entry)

def is_block_period(client_ip):
    current_time = datetime.datetime.now().time()
    # Check if the client IP is whitelisted
    if client_ip in WHITELIST:
        return False
    # Check if it's within the block period
    return BLOCK_START_TIME <= current_time or current_time < BLOCK_END_TIME


class DNSRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        # Get the client IP address
        client_ip = self.client_address[0]
        # Handle the DNS request only if it's not within the block period
        if not is_block_period(client_ip):
            query = dns.message.from_wire(self.request[0])
            domain = str(query.question[0].name)
            # Print the domain being requested
            print(datetime.datetime.now(), " : ", client_ip, " : ", domain,)
            # Log the request to a file
            log_request(domain, client_ip)
            # Create a response message
            response = dns.message.make_response(query)

            # Check if the domain is in the blacklist
            if any(word in domain for word in BLACKLIST) and client_ip not in WHITELIST:
                print("BLACKLISTED")
                # Set the response code to indicate non-existent domain
                response.set_rcode(dns.rcode.NXDOMAIN)
                # Set an empty answer section to indicate "Not found" response
                response.answer = []
            else:
                # Forward the request to the upstream DNS server
                response = dns.query.tcp(query, UPSTREAM_DNS)

            # Send the DNS response back to the client
            self.request[1].sendto(response.to_wire(), self.client_address)
        else:
            print("DNS requests blocked during the specified period.")

# Create a DNS server instance
dns_server = socketserver.ThreadingUDPServer((LISTEN_ADDRESS, LISTEN_PORT), DNSRequestHandler)

# Start the DNS server in a separate thread
dns_server_thread = threading.Thread(target=dns_server.serve_forever)
dns_server_thread.start()

print(f'DNS server started on {LISTEN_ADDRESS}:{LISTEN_PORT}')
print(f'Upstream DNS server: {UPSTREAM_DNS}')
print('Blacklisted domains:')
for domain in BLACKLIST:
    print(f'- {domain}')
print('Whitelisted IP addresses:')
for ip in WHITELIST:
    print(f'- {ip}')

# Keep the main thread running until interrupted
try:
    while True:
        pass
except KeyboardInterrupt:
    # Stop the DNS server and join the thread
    dns_server.shutdown()
    dns_server_thread.join()
