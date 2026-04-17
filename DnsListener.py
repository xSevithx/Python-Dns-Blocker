import dns.message
import dns.query
import dns.rcode
import dns.resolver
import socketserver
import threading
import datetime
import logging
import os
import signal
import sys

LISTEN_ADDRESS = '0.0.0.0'
LISTEN_PORT = 53
UPSTREAM_DNS = os.environ.get('UPSTREAM_DNS', '8.8.8.8')

BLACKLIST = set(
    entry.strip().lower()
    for entry in os.environ.get('BLACKLIST', 'youtube,youtubekids,youtubei').split(',')
    if entry.strip()
)

WHITELIST = set(
    entry.strip()
    for entry in os.environ.get('WHITELIST', '').split(',')
    if entry.strip()
)

BLOCK_START_HOUR = int(os.environ.get('BLOCK_START_HOUR', '13'))
BLOCK_START_MINUTE = int(os.environ.get('BLOCK_START_MINUTE', '0'))
BLOCK_END_HOUR = int(os.environ.get('BLOCK_END_HOUR', '8'))
BLOCK_END_MINUTE = int(os.environ.get('BLOCK_END_MINUTE', '0'))

BLOCK_START_TIME = datetime.time(BLOCK_START_HOUR, BLOCK_START_MINUTE)
BLOCK_END_TIME = datetime.time(BLOCK_END_HOUR, BLOCK_END_MINUTE)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('dns_log.txt'),
    ],
)
logger = logging.getLogger('dns-blocker')


def is_block_period(client_ip):
    if client_ip in WHITELIST:
        return False
    current_time = datetime.datetime.now().time()
    if BLOCK_START_TIME <= BLOCK_END_TIME:
        return BLOCK_START_TIME <= current_time < BLOCK_END_TIME
    # Wraps midnight (e.g. 13:00 -> 08:00)
    return current_time >= BLOCK_START_TIME or current_time < BLOCK_END_TIME


def is_blacklisted(domain):
    domain_lower = domain.lower().rstrip('.')
    labels = domain_lower.split('.')
    return any(label in BLACKLIST for label in labels)


def make_blocked_response(query):
    response = dns.message.make_response(query)
    response.set_rcode(dns.rcode.NXDOMAIN)
    response.answer = []
    return response


class DNSRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        client_ip = self.client_address[0]
        try:
            query = dns.message.from_wire(self.request[0])
        except Exception:
            logger.warning(f"Malformed DNS packet from {client_ip}")
            return

        domain = str(query.question[0].name)

        if is_block_period(client_ip):
            logger.info(f"TIME-BLOCK  {client_ip}  {domain}")
            response = make_blocked_response(query)
            self.request[1].sendto(response.to_wire(), self.client_address)
            return

        if is_blacklisted(domain) and client_ip not in WHITELIST:
            logger.info(f"BLACKLISTED {client_ip}  {domain}")
            response = make_blocked_response(query)
        else:
            logger.info(f"FORWARD     {client_ip}  {domain}")
            try:
                response = dns.query.udp(query, UPSTREAM_DNS, timeout=5)
            except Exception as e:
                logger.error(f"Upstream DNS error for {domain}: {e}")
                response = make_blocked_response(query)

        self.request[1].sendto(response.to_wire(), self.client_address)


def main():
    server = socketserver.ThreadingUDPServer(
        (LISTEN_ADDRESS, LISTEN_PORT), DNSRequestHandler
    )

    logger.info(f"DNS server listening on {LISTEN_ADDRESS}:{LISTEN_PORT}")
    logger.info(f"Upstream DNS: {UPSTREAM_DNS}")
    logger.info(f"Blacklist: {sorted(BLACKLIST)}")
    logger.info(f"Whitelist: {sorted(WHITELIST) if WHITELIST else '(none)'}")
    logger.info(f"Block window: {BLOCK_START_TIME} - {BLOCK_END_TIME}")

    shutdown_event = threading.Event()

    def graceful_shutdown(signum, frame):
        logger.info("Shutting down...")
        server.shutdown()
        shutdown_event.set()

    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()

    shutdown_event.wait()
    server_thread.join()


if __name__ == '__main__':
    main()
