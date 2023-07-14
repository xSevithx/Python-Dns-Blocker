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
BLACKLIST = ['youtube.com.', 'www.youtube.com.', 'youtubekids.com.', 'www.youtubekids.com.', 'm.youtube.com.', 'm.youtubekids.com.']

# Whitelisted IP addresses
WHITELIST = ['192.168.1.7']

class DNSRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        # Get the client IP address
        client_ip = self.client_address[0]

        # Handle the DNS request
        query = dns.message.from_wire(self.request[0])
        domain = str(query.question[0].name)

        # Print the domain being requested
        print(datetime.datetime.now(), " : ", domain)

        # Create a response message
        response = dns.message.make_response(query)

        # Check if the domain is in the blacklist
        if domain in BLACKLIST and client_ip not in WHITELIST:
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
