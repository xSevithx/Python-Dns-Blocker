# DNS Blocker

A lightweight DNS proxy that blocks requests to blacklisted domains (e.g. YouTube) and supports independent time windows for full internet shutoff and blacklist enforcement, plus IP whitelisting.

## Features

- **Domain blacklisting** — blocks DNS resolution for specified domains (returns NXDOMAIN)
- **Full shutoff window** — kill all internet for non-whitelisted IPs during set hours (e.g. bedtime)
- **Blacklist enforcement window** — only enforce the blacklist during certain hours (allow as a reward outside those hours)
- **IP whitelisting** — exempt specific devices from all blocking
- **Upstream forwarding** — non-blocked queries are forwarded to an upstream DNS server (default: Google 8.8.8.8)
- **Logging** — all requests are logged to stdout and `dns_log.txt`

## Quick Start with Docker

1. Edit `.env` with your settings
2. Run:

```bash
docker compose up -d
```

3. Point your router's or device's DNS to the IP of the machine running this container.

## Configuration

All settings live in the `.env` file:

| Variable        | Default                        | Description                                            |
|-----------------|--------------------------------|--------------------------------------------------------|
| `UPSTREAM_DNS`  | `8.8.8.8`                      | DNS server to forward non-blocked queries to           |
| `BLACKLIST`     | `youtube,youtubekids,youtubei` | Comma-separated domain keywords to block               |
| `WHITELIST`     | *(empty)*                      | Comma-separated IPs exempt from all blocking           |
| `SHUTOFF_START` | `01:00`                        | When full internet shutoff begins (HH:MM, 24h)        |
| `SHUTOFF_END`   | `08:00`                        | When full internet shutoff ends                        |
| `ENFORCE_START` | `08:00`                        | When blacklist enforcement begins                      |
| `ENFORCE_END`   | `23:00`                        | When blacklist enforcement ends                        |

### Time Window Behavior

```
midnight                                                      midnight
  |  SHUTOFF (all blocked)  |        ENFORCE (blacklist active)       | FREE |SHUTOFF
  0  ·  ·  1:00 · · · · 8:00 · · · · · · · · · · · · · · 23:00 · · 1:00
```

- **During SHUTOFF** — all DNS is blocked for non-whitelisted IPs (no internet at all)
- **During ENFORCE** — only blacklisted domains are blocked, everything else works
- **Outside both** — everything is open, including blacklisted domains (reward time)
- **Whitelisted IPs** — always have full unrestricted access

Set start and end to the same value to make a window always-on (e.g. `ENFORCE_START=00:00` / `ENFORCE_END=00:00` = blacklist enforced 24/7).

## Running Without Docker

```bash
pip install -r requirements.txt
# Set env vars or export from .env, then:
sudo python DnsListener.py
```

> Port 53 requires root/admin privileges.

## Important Notes

- **DNS-over-HTTPS bypass**: Tech-savvy users can bypass plain DNS blocking by enabling DoH in their browser. To mitigate this, disable DoH in browser settings or block known DoH endpoints at the firewall level.
- **Router integration**: For whole-network blocking, set this server's IP as the primary DNS on your router.
