import dns.message
import dns.query
import dns.rcode
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


def parse_time(env_var, default):
    raw = os.environ.get(env_var, default).strip()
    parts = raw.split(':')
    return datetime.time(int(parts[0]), int(parts[1]))


SHUTOFF_START = parse_time('SHUTOFF_START', '01:00')
SHUTOFF_END = parse_time('SHUTOFF_END', '08:00')
ENFORCE_START = parse_time('ENFORCE_START', '08:00')
ENFORCE_END = parse_time('ENFORCE_END', '23:00')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('dns_log.txt'),
    ],
)
logger = logging.getLogger('dns-blocker')


def in_time_range(now, start, end):
    """Check if `now` falls within [start, end). Handles midnight wrap."""
    if start == end:
        return True
    if start < end:
        return start <= now < end
    return now >= start or now < end


def is_shutoff(client_ip):
    if client_ip in WHITELIST:
        return False
    if SHUTOFF_START == SHUTOFF_END:
        return False
    return in_time_range(datetime.datetime.now().time(), SHUTOFF_START, SHUTOFF_END)


def is_enforcing():
    if ENFORCE_START == ENFORCE_END:
        return True
    return in_time_range(datetime.datetime.now().time(), ENFORCE_START, ENFORCE_END)


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

        # Priority 1: full shutoff (kills all internet)
        if is_shutoff(client_ip):
            logger.info(f"SHUTOFF     {client_ip}  {domain}")
            response = make_blocked_response(query)
            self.request[1].sendto(response.to_wire(), self.client_address)
            return

        # Priority 2: blacklist enforcement (only during enforce window)
        if is_enforcing() and is_blacklisted(domain) and client_ip not in WHITELIST:
            logger.info(f"BLOCKED     {client_ip}  {domain}")
            response = make_blocked_response(query)
            self.request[1].sendto(response.to_wire(), self.client_address)
            return

        # Otherwise: forward upstream
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
    if SHUTOFF_START == SHUTOFF_END:
        logger.info("Shutoff window: DISABLED")
    else:
        logger.info(f"Shutoff window: {SHUTOFF_START} - {SHUTOFF_END}")
    if ENFORCE_START == ENFORCE_END:
        logger.info("Enforce window: ALWAYS (24/7)")
    else:
        logger.info(f"Enforce window: {ENFORCE_START} - {ENFORCE_END}")

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
