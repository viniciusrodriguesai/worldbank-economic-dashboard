# Secure deployment guide

## Status

This repository is deploy-ready but was not deployed by this work. No hosting
account, DNS zone, TLS certificate, or deployment credential was available. The
remaining external step is to provision those resources and deploy the reviewed images.

## Architecture

```text
Internet -> TLS edge -> frontend nginx :8080 -> backend :8000 -> World Bank API
```

Compose publishes only the frontend on loopback by default. FastAPI remains internal.
nginx serves the Vite production build and proxies same-origin `/api` requests; the Vite
development server is not part of production.

Both runtime containers run as non-root, drop Linux capabilities, set
`no-new-privileges`, use read-only roots with bounded temporary filesystems, define
CPU/memory limits and health checks, and pin official images to reviewed digests.

## Local production-equivalent run

With Docker Engine and Compose v2 running:

```powershell
Copy-Item .env.example .env
docker compose config
docker compose up --build
```

Open `http://localhost:8080`. Stop with `docker compose down`. The local `.env`
file is ignored by Git.

## Configuration

| Variable | Scope | Default | Security notes |
| --- | --- | --- | --- |
| `WB_API_BASE` | Backend runtime | World Bank HTTPS API | Trusted server configuration; the application rejects credentials and unsafe URLs. |
| `CORS_ORIGINS` | Backend runtime | Local origins | Exact HTTP(S) origins only; never use wildcard production CORS. |
| `DASHBOARD_BIND_ADDRESS` | Compose host | `127.0.0.1` | Keep loopback when the TLS proxy is on the same host. |
| `VITE_API_BASE_URL` | Frontend build | `/api` | Public browser configuration only; never place secrets in `VITE_` variables. |

No application secret is required today. Future secrets must be injected at runtime
through a platform secret store, never through build arguments, frontend variables,
committed Compose values, or image layers.

## TLS and reverse proxy

The included nginx container is an HTTP application server, not the public TLS edge.
A production load balancer, ingress, reverse proxy, or CDN must terminate TLS, redirect
HTTP to HTTPS, restrict backend port 8000, and add HSTS only after the domain is confirmed
HTTPS-only.

The frontend nginx owns browser-document controls and sets CSP, clickjacking, MIME
sniffing, referrer, and permissions headers. FastAPI intentionally does not add
document-only headers. The CSP permits self-hosted assets and OpenStreetMap tile images.

API proxy traffic is limited to 20 requests/second per observed source with a burst of
40. Behind another proxy, trust forwarded client IPs only from explicitly configured
proxy addresses; never accept arbitrary `X-Forwarded-For` values.

## Health and capacity

- Frontend liveness: `GET /health` on port 8080.
- Backend liveness: internal `GET /health` on port 8000.
- Proxied backend liveness: `GET /api/health`.

Backend liveness deliberately does not call the World Bank. Monitor latency, 429, 5xx,
and upstream timeout rates separately.

The default backend has one Uvicorn worker, two forecast slots, one CPU and 1 GiB memory.
Scale with container replicas and equivalent per-replica limits. Each replica owns its
in-memory cache and forecast semaphore. Do not expand model candidates, ranges, workers,
or concurrency without load testing.

## Verification and maintenance

Dependabot monitors both Dockerfiles. Review digest updates and run:

```powershell
docker buildx imagetools inspect python:3.11-slim-bookworm
docker buildx imagetools inspect node:22.15.0-alpine
docker buildx imagetools inspect nginx:1.28-alpine
docker compose config
docker compose build --pull
docker compose up -d
docker compose ps
```

Then smoke-test `/health`, `/api/health`, metadata, indicator search, comparison, and an
evaluated forecast. Scan final images with the registry or platform scanner before
promotion. Roll back by deploying the previous reviewed image digest.

## Remaining production steps

1. Provision the host/platform, DNS, TLS, and deployment credentials.
2. Store credentials only in the platform secret manager.
3. Keep backend port 8000 private and configure the TLS edge.
4. Set exact production CORS origins if direct browser-to-API access is needed.
5. Configure logs, alerts, egress policy, image scanning, and resource monitoring.
