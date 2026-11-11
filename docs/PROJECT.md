# ledgernode

Household money visibility for two people, self-hosted and privately owned.

## Problem

Spending is spread across bank accounts, apps and spreadsheets. Nobody in the household can answer
"where did last month's money go?" without opening several of them, and the data cannot be taken
elsewhere when needed.

## Goal

Run a single, private finance manager that shows both people what actually happened last month,
next to the month before, and keeps the underlying data exportable.

## What we run

[Firefly III](https://www.firefly-iii.org/) — a free and open-source personal finance manager. It
provides double-entry bookkeeping, multi-currency transactions, a rules engine, budgets, categories,
tags, reports, a JSON REST API, and built-in CSV export of transactions.

It deliberately does **no** forecasting, prediction, or advanced accounting. It makes the truth
visible; it does not advise.

## Who it serves

| Person | Role | Needs |
|---|---|---|
| Primary owner | Sets everything up, does the importing, maintains it | Import statement exports, define categorisation rules, read reports, take data out |
| Partner | Uses it when she wants to | View everything, add and edit transactions from her phone |

Both people use the same household books. They share one login — see accepted limitations.

## In scope for v1

- One instance on the home network, reachable from both people's phones over home Wi-Fi, never
  exposed to the internet.
- One bank account (Bank A) with two years of real history imported from the bank's own CSV
  export.
- Rules that categorise the top recurring merchants automatically.
- Monthly report for the last month with the previous month alongside it, for comparison.
- CSV export of transactions that opens in a spreadsheet.
- Data survives restarts, and a documented backup/restore step exists.
- Sign-in protected by a password plus a second factor.

## Out of scope for v1

| Excluded | Reason |
|---|---|
| Separate logins per person, view-only rights, or per-person attribution | Not possible in Firefly III; see accepted limitations |
| Internet exposure (tunnels, reverse proxies, public DNS) | A home tool for two people does not need to be reachable from anywhere; not exposing it removes a whole class of risk |
| Automatic bank sync | Depends on paid, region-limited third-party aggregators; the bank's free CSV export is sufficient |
| ~~Budgets, piggy banks, savings goals~~ | **Moved into scope 2026-11-10 as US-004** — bare reporting could not show whether a plan was being followed; see [ADR-0004](decisions/0004-budget-and-debt-scope.md) |
| Multi-currency | One household, one currency |
| Third-party mobile apps, custom code, integrations | The product already exists; nothing to build |
| Monitoring, high availability, upgrade automation | Disproportionate for a two-person home tool |
| Using CSV export as a backup | The vendor explicitly warns against it |

## Accepted limitations

These were considered and consciously accepted, not overlooked:

1. **One shared login for both people.** Firefly III keeps every user's financial administration
   strictly separate and offers no way to share one administration with another user; the vendor's
   documented workaround is sharing a password, and a proper sharing model is an open-ended upstream
   project. Consequences: no separate identities, no view-only access for the partner, and no record
   of who entered which transaction.
2. **CSV export is not a backup.** Export is for using the data elsewhere; recovery depends on
   backing up the underlying data store directly, as the vendor instructs.
3. **No advice, only visibility.** Firefly III will not forecast, plan, or recommend. Judgement stays
   with the people.
4. **Traffic inside the home network is unencrypted.** Decided 2026-11-09: the home network is trusted,
   the instance is never exposed to the internet, and signing in still requires a password plus a second
   factor. To be revisited before any form of remote access is considered.

## Source of truth for requirements

- [US-001 — Household money visibility with data we can take with us](stories/US-001-household-money-visibility.md)
- [US-004 — A budget and debt picture that matches reality](stories/US-004-budget-and-debt-visibility.md)
  — added 2026-11-10, decision in [ADR-0004](decisions/0004-budget-and-debt-scope.md)

## Status

Requirements agreed (2026-11-09) and handed to delivery the same day.

- Story: US-001, status **Ready for development**.
- Delivery plan and task breakdown: [tasks/sprint.md](../tasks/sprint.md).
- Deferred and rejected work: [tasks/backlog.md](../tasks/backlog.md).
- Hosting and backup decision: [docs/decisions/0001-hosting-and-backup.md](decisions/0001-hosting-and-backup.md).
- Live instance: `http://192.168.1.10:8090` on `host-a`, running Firefly III 6.7.9 against
  PostgreSQL 18 (2026-11-09).

Two open decisions are blocking delivery and are tracked in the sprint file (E-1: whether the home-LAN
connection must be encrypted or the criterion is amended; E-2: whether the bank's CSV export includes
pending transactions).
