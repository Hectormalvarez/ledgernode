# ADR-0001 — Host the household instance on `host-a` with the vendor's Docker layout

| | |
|---|---|
| **Status** | Accepted, 2026-11-09 |
| **Tasks** | T-01 (hosting), T-02 (backup and restore) |
| **Story** | [US-001](../stories/US-001-household-money-visibility.md) |
| **Deciders** | Household owner, delivery |

## Context — facts gathered on 2026-11-09

**Host `host-a`** (reached over SSH as `admin`): Ubuntu 26.04.1 LTS, x86_64, 8 cores, 30 GiB RAM,
350 GiB free on `/`, Docker 29.1.3 with Compose v5.7.0, passwordless `sudo` available, `ufw` unit
running but **not filtering**. LAN addresses `192.168.1.10` (wired `br0`) and `192.168.1.11`
(Wi-Fi). Ports 8080, 8070, 8090 and 9080 are free.

**Already running on the same host**, and not to be disturbed: jellyfin, dispatcharr, watchstate
(:8081), redis (:6379), a Postgres exposed on `0.0.0.0:5432`, three web stacks behind cloudflared
(:9417, :9418, :9150) and a second cloudflared tunnel.

**Vendor constraints:** the Docker installation requires a database container — "Without such a
database container, Firefly III will not work" — so a single-container or SQLite setup is not
supported. The canonical compose is `app` + `mariadb` + an `alpine` cron sidecar that calls
`/api/v1/cron/$STATIC_CRON_TOKEN`.

**Bank export facts** (completing T-06 against the real file): 2,268 settled rows spanning
2024-11-09 → 2026-11-09; the header is line 1 with no banner (R-11 closed); `MM/DD/YY` is proven
month-first because day-of-month reaches 31 (R-9 closed); direction comes from `Transaction Type`,
proven by 2,267 of 2,267 consecutive balance deltas matching ±amount (R-10 closed); exactly one
`Debit` row carries an already-negative amount (a POS reversal) that must not be normalised; and 21
groups of genuinely identical date+description+amount rows exist, all of which must survive import.

## Decision

1. **Host.** `host-a`, alongside the existing stacks, in its own compose project and its own bridge
   network so nothing collides.
2. **Deployment.** The vendor's three-service layout, `infra/firefly/docker-compose.yml`, with **pinned
   tags** (`fireflyiii/core:version-6.7.9`, `postgres:18-alpine`, `alpine:3.20`) instead of `:latest`.
   Deviations from the vendor file are commented inline. The database is **PostgreSQL 18**, chosen by
   the owner over the vendor's default MariaDB; this is a supported configuration (the vendor documents
   the `pgsql`/`5432`/`POSTGRES_*` changes), and PostgreSQL 18 keeps its cluster in
   `/var/lib/postgresql`, so that — not the familiar `/var/lib/postgresql/data` — is the mount point.
3. **Data location.** Bind mounts under `/srv/ledgernode/data/{upload,db}` rather than named volumes,
   so a backup is an ordinary file copy and a restore is an untar — directly serving AC12.
4. **Exposure.** Published as `192.168.1.10:8090` only. No router forwarding, no tunnel, no public
   DNS. Plaintext on the LAN is accepted (US-001 limitation 5), not overlooked.
5. **Backup and restore (T-02).** Nightly `tar.gz` of `/srv/ledgernode/data` plus a logical dump of the
   database; restore is untar + import dump. Owner performs it weekly; the exact commands live in the
   runbook (T-15) so the procedure is not folklore.
6. **Version policy.** `:latest` is banned in this stack. Upgrading is a deliberate tag bump, a fresh
   backup, a restart and a verification pass.

## Consequences

**Positive:** no new hardware; a host already proven to run containers; backups reduced to file
operations; the instance cannot be reached from outside the house by construction.

**Negative, and accepted:**
- Uptime is a *laptop's* uptime. Suspend, lid-close or reboot takes both the instance and the cron
  sidecar down. Recorded as risk R-12.
- The books share a host with media and web stacks: disk and CPU contention is possible, and a
  compromise of any container on this host is a compromise of the household finances.
- Port 8090 is unencrypted on the LAN by explicit decision.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| MariaDB (the vendor default) | The owner asked for PostgreSQL. Nothing in US-001 depends on the vendor default, and PostgreSQL 18 is a documented, supported option |
| Named Docker volumes | Backup would need root tar into `/var/lib/docker`, making AC12 harder to prove |
| Native install on the host | More moving parts to maintain and roll back; no pinning benefit |
| A dedicated machine | No benefit for two users on one LAN; new hardware and power for nothing |
| SQLite / single container | Not supported by the vendor's Docker image |
