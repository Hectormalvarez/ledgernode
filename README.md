# ledgernode

Private household finance for two people, self-hosted. One
[Firefly III](https://www.firefly-iii.org/) instance on the home network is the system of
record; this repository keeps the infrastructure plan and the tooling that grows up around it.

- How and where it runs: [docs/infra-plan.md](docs/infra-plan.md) — host-a, LAN-only,
  never exposed to the internet.
- Real names, institutions, balances and tokens never get committed; `.gitignore` enforces
  it and the local-only files that hold them are kept out of git on purpose.
- Status: restarted from scratch on 2026-11-16. Everything that existed before is archived
  at `~/Projects/Lab/ledgernode-archive-20261116/` (see its `RESTORE.md`), in case a decision
  made by the previous attempt turns out to have been worth keeping.
