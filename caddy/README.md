# Tinypost Caddy

Reverse proxy for custom domain TLS. Uses Caddy's on-demand TLS to automatically provision certificates for user custom domains.

## How it works

- Custom domains point their A/AAAA records to this app's IPs
- Caddy receives the request and provisions a TLS certificate on first connect
- Before issuing a cert, Caddy asks the backend (`/_tls/ask`) to verify the domain is valid
- Requests are reverse-proxied to the backend with the original Host header preserved

## Environment variables

| Variable | Description | Example |
|---|---|---|
| `BACKEND` | Fly.io hostname of the Tinypost app | `tinypost.fly.dev` |
| `CADDY_HOST` | Hostname of this Caddy app | `tinypost-caddy.fly.dev` |
| `CADDY_ASK_TOKEN` | Shared secret for the `/_tls/ask` endpoint | |

## Deploy

```sh
cd caddy
fly launch --no-deploy -c fly.toml
fly volumes create caddy_data --size 1 -a tinypost-caddy
fly secrets set BACKEND=tinypost.fly.dev CADDY_HOST=tinypost-caddy.fly.dev CADDY_ASK_TOKEN=<token> -a tinypost-caddy
fly deploy -c fly.toml -a tinypost-caddy
fly ips allocate-v4 -a tinypost-caddy
fly ips allocate-v6 -a tinypost-caddy
```

The allocated IPs are what users point their A/AAAA records to. Set the same `CADDY_ASK_TOKEN` on the main Tinypost app.
