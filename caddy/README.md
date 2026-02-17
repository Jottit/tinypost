# Jottit Caddy

Reverse proxy for custom domain TLS. Uses Caddy's on-demand TLS to automatically provision certificates for user custom domains.

## How it works

- Custom domains point their A/AAAA records to this app's IPs
- Caddy receives the request and provisions a TLS certificate on first connect
- Before issuing a cert, Caddy asks the backend (`/_tls/ask`) to verify the domain is valid
- Requests are reverse-proxied to the backend with the original Host header preserved

## Environment variables

| Variable | Description | Example |
|---|---|---|
| `BACKEND` | Fly.io hostname of the Jottit app | `jottit.fly.dev` |
| `CADDY_HOST` | Hostname of this Caddy app | `jottit-caddy.fly.dev` |
| `CADDY_ASK_TOKEN` | Shared secret for the `/_tls/ask` endpoint | |

## Deploy

```sh
cd caddy
fly launch --no-deploy -c fly.toml
fly volumes create caddy_data --size 1 -a jottit-caddy
fly secrets set BACKEND=jottit.fly.dev CADDY_HOST=jottit-caddy.fly.dev CADDY_ASK_TOKEN=<token> -a jottit-caddy
fly deploy -c fly.toml -a jottit-caddy
fly ips allocate-v4 -a jottit-caddy
fly ips allocate-v6 -a jottit-caddy
```

The allocated IPs are what users point their A/AAAA records to. Set the same `CADDY_ASK_TOKEN` on the main Jottit app.
