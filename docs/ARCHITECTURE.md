# Architecture

What runs, where it runs, and where the data lives. Decisions and their reasoning live in
`docs/decisions/`; this file is only the map.

## Host

Everything runs on **`host-a`** (Ubuntu 26.04 LTS, 8 cores, 30 GiB RAM, Docker 29.1.3), a home
laptop configured never to suspend. It also runs unrelated media and web stacks, so this project owns
its own compose project and bridge network. LAN address `192.168.1.10`. **Nothing is exposed to the
internet** — no tunnel, no port forwarding, no public DNS.

## Containers

Compose project `ledgernode`, deployed at `/srv/ledgernode` (source of truth: `infra/firefly/`).

| Service | Image (pinned) | Published | Role |
|---|---|---|---|
| `ledgernode-app` | `fireflyiii/core:version-6.7.9` | `192.168.1.10:8090` | Web UI and JSON REST API |
| `ledgernode-db` | `postgres:18-alpine` | internal only | Data store |
| `ledgernode-cron` | `alpine:3.20` | none | Calls the nightly job endpoint |
| `ledgernode-importer` | `fireflyiii/data-importer:version-2.3.5` | `192.168.1.10:8091` | CSV import (UI, plus CLI variant) |

## Data

| Path | Holds |
|---|---|
| `/srv/ledgernode/data/upload` | Firefly III uploads (bind mount) |
| `/srv/ledgernode/data/db` | PostgreSQL 18 cluster, at `data/db/18` |
| `/srv/ledgernode/import` | Statement files staged for import (mounted at `/import`) |

Bind mounts, not named volumes, so a backup is an ordinary file copy (ADR-0001).

## Secrets

| File | Holds | Mode |
|---|---|---|
| `/srv/ledgernode/.env` | `APP_KEY`, database credentials, cron token | 600 |
| `/srv/ledgernode/.db.env` | `POSTGRES_*` | 600 |
| `/srv/ledgernode/.importer.env` | Personal access token (expires 2027-11-09) | 600 |

All three are git-ignored; the repository carries only `*.example` templates.

## Boundaries

```text
browser (LAN)  ──►  app:8090  ──►  db:5432
browser (LAN)  ──►  importer:8091  ──►  app:8080  ──►  db:5432
tools/verify_import.py  ──►  app:8090 API only  (never the database)
```

The verification tool talks to the API exclusively. It never opens a database connection, because the
API recalculates cached balances and raw SQL does not.

## Backup and recovery

A `tar` of `/srv/ledgernode/data` plus a logical database dump. Restore is untar plus dump import.
CSV export is **not** a backup (US-001 limitation 3). A restore has not yet been rehearsed — that is
task T-13, and it gates any tooling that writes to the ledger.

## Deliberately absent

No TLS on the LAN (US-001 limitation 5). No monitoring, no high availability, no upgrade automation,
no per-user identity — one shared login, by decision (US-001 limitation 1).
