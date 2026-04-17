# DNS Blocker

A lightweight DNS proxy that blocks requests to blacklisted domains (e.g. YouTube) and supports time-based blocking schedules and IP whitelisting.

## Features

- **Domain blacklisting** — blocks DNS resolution for specified domains (returns NXDOMAIN)
- **Time-based blocking** — only block during configured hours (e.g. 1 PM to 8 AM)
- **IP whitelisting** — exempt specific devices from all blocking
- **Upstream forwarding** — non-blocked queries are forwarded to an upstream DNS server (default: Google 8.8.8.8)
- **Logging** — all requests are logged to stdout and `dns_log.txt`

## Quick Start with Docker

```bash
docker compose up -d
```

Then point your router's or device's DNS settings to the IP of the machine running this container.

## Configuration

All settings are controlled via environment variables in `docker-compose.yml`:

| Variable             | Default                         | Description                                  |
|----------------------|---------------------------------|----------------------------------------------|
| `UPSTREAM_DNS`       | `8.8.8.8`                       | DNS server to forward non-blocked queries to |
| `BLACKLIST`          | `youtube,youtubekids,youtubei`  | Comma-separated domain keywords to block     |
| `WHITELIST`          | *(empty)*                       | Comma-separated IPs exempt from blocking     |
| `BLOCK_START_HOUR`   | `13`                            | Hour (24h) when time-based blocking starts   |
| `BLOCK_START_MINUTE` | `0`                             | Minute when time-based blocking starts       |
| `BLOCK_END_HOUR`     | `8`                             | Hour (24h) when time-based blocking ends     |
| `BLOCK_END_MINUTE`   | `0`                             | Minute when time-based blocking ends         |

## Running Without Docker

```bash
pip install -r requirements.txt
sudo python DnsListener.py
```

> Port 53 requires root/admin privileges.

## How It Works

1. The server listens for UDP DNS queries on port 53
2. If the requesting client IP is whitelisted, the query is always forwarded
3. If the current time falls within the block window, all queries from non-whitelisted IPs are blocked
4. Otherwise, queries matching the blacklist return NXDOMAIN; all others are forwarded upstream

## Important Notes

- **DNS-over-HTTPS bypass**: Tech-savvy users can bypass plain DNS blocking by enabling DoH in their browser. To mitigate this, disable DoH in browser settings or block known DoH endpoints at the firewall level.
- **Router integration**: For whole-network blocking, set this server's IP as the primary DNS on your router.
