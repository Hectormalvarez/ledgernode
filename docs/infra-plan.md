# Infrastructure plan

The facts needed to operate, back up and rebuild the household instance on host-a.
Written 2026-11-16 when this repository was restarted; verify against the running stack
before relying on it — the host was offline on that date and its IP may have changed.

## Host

**host-a** — home laptop, Ubuntu 26.04 LTS, Docker. LAN address `192.168.1.10`.
Never exposed to the internet: no tunnel, no port forwarding, no public DNS. No TLS on the
trusted home LAN; sign-in requires password + second factor.

## Services — compose project `ledgernode`, deployed at `/srv/ledgernode`

| Service | Image (pinned) | Published | Role |
|---|---|---|---|
| `ledgernode-app` | `fireflyiii/core:version-6.7.9` | `192.168.1.10:8090` | Web UI + JSON API |
| `ledgernode-db` | `postgres:18-alpine` | internal only | Data store |
| `ledgernode-cron` | `alpine:3.20` | none | Nightly job |
| `ledgernode-importer` | `fireflyiii/data-importer:version-2.3.5` | `192.168.1.10:8091` | CSV import |

## Data — bind mounts, so a backup is an ordinary file copy

| Path | Holds |
|---|---|
| `/srv/ledgernode/data/upload` | Firefly III uploads |
| `/srv/ledgernode/data/db` | PostgreSQL 18 cluster (`data/db/18`) |
| `/srv/ledgernode/import` | Statement files staged for import (mounted at `/import`) |

## Secrets — mode 600, git-ignored; the repo carries only `*.example` templates

- `/srv/ledgernode/.env` — `APP_KEY`, database credentials, cron token
- `/srv/ledgernode/.db.env` — `POSTGRES_*`
- `/srv/ledgernode/.importer.env` — personal access token, **expires 2027-11-09 — rotate before then**
- local: `.household.env` (real names, institutions, balances) and `docs/plans/*.md` with live figures

## Backup — CSV export is NOT a backup

A `tar` of `/srv/ledgernode/data` plus a logical dump (`pg_dump`). Restore is untar + dump
import. **Outstanding: rehearse a full restore once** — it gates anything that ever writes
to the ledger.

## Predecessor material

The pre-restart repository (ADRs, import-verification tools, PDF parsers, tests, full git
history) is archived at `~/Projects/Lab/ledgernode-archive-20261116/` — recoverable via its
`RESTORE.md`.
