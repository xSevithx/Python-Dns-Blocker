import dns.message
import dns.rcode
import dns.resolver
import socketserver
import threading

blacklist = ['youtube.com', 'youtubekids.com']

class DNSRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        # Handle the DNS request
        query = dns.message.from_wire(self.request[0])
        domain = str(query.question[0].name)
        
        # Check if the domain is in the blacklist
        if domain in blacklist:
            # Block the request
            response = dns.message.make_response(query)
            response.set_rcode(dns.rcode.REFUSED)
        else:
            # Forward the request to an upstream DNS resolver
            resolver = dns.resolver.Resolver()
            response = resolver.resolve(domain, query.rdtype)
        
        # Send the DNS response back to the client
        self.request[1].sendto(response.to_wire(file=None, wire=None), self.client_address)

dns_server = socketserver.ThreadingUDPServer(('0.0.0.0', 53), DNSRequestHandler)

dns_server_thread = threading.Thread(target=dns_server.serve_forever)
dns_server_thread.start()

try:
    while True:
        pass
except KeyboardInterrupt:
    dns_server.shutdown()
    dns_server_thread.join()
