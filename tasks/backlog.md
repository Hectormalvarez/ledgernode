# Backlog

Work that is **not** in the current sprint. Nothing here starts without the Product Owner agreeing it
and a human approving the scope change. Items move to a sprint only when their trigger is met — that is
what stops "while we're in here" from quietly becoming the plan.

Current sprint: [sprint.md](sprint.md) · Story: [US-001](../docs/stories/US-001-household-money-visibility.md)

## Next candidates — after US-001 is proven

| ID | Item | Origin | Trigger to pull it | Notes |
|---|---|---|---|---|
| B-01 | Per-person attribution through a tagging convention (each person tags their own entries) | US-001 accepted limitation 1 | The partner is genuinely using the books and "whose spending was this?" starts coming up | The product cannot distinguish users, so this is a habit decision, not a feature. Cheap to try, easy to abandon |
| B-02 | ~~Budgets with monthly limits~~ | US-001 out of scope | **Trigger met 2026-11-10 — moved to [US-004](../docs/stories/US-004-budget-and-debt-visibility.md)** | Two years of history are imported and bare reporting cannot show whether a plan is followed. Delivered as budgets with `reset`/`rollover` limits |
| B-03 | Operating runbook refinements / upgrade cadence tuning | US-001 T-15 | The first upgrade or the first missed backup | Improves an existing artefact rather than adding scope |

## Later — real ideas, not yet justified

| ID | Item | Origin | Trigger to pull it | Notes |
|---|---|---|---|---|
| B-04 | Remote access from outside the home network | PO scope decision (v1) | Accessing finances while away stops being hypothetical | Must bring its own encryption decision: E-1 settled the home LAN only, and unencrypted traffic over the internet is a different proposition |
| B-05 | Automatic bank sync through an aggregator | US-001 out of scope | Monthly CSV importing becomes a chore that actually gets skipped | Paid and region-limited; would replace part of the T-08 procedure |
| B-06 | Upgrade automation and basic monitoring | US-001 out of scope | A missed upgrade or a silent outage causes real friction | Only once the instance matters enough to be forgotten about |
| B-07 | ~~Savings goals / piggy banks~~ | US-001 out of scope | **Trigger met 2026-11-10 — moved to [US-004](../docs/stories/US-004-budget-and-debt-visibility.md)** | Delivered as piggy banks for an emergency buffer, a settlement fund and the student-loan resumption fund. Still no forecasting: piggy banks show progress, not projections |
| B-08 | Multi-currency | US-001 out of scope | A second currency genuinely enters household spending | |
| B-09 | Analysis of exported data in an external tool | US-001 AC10 | The built-in report stops being enough | Export already works; this is about what happens downstream of it |
| B-10 | Adopt the vendor's sharing-with-roles model, if it ships | US-001 accepted limitation 1 | The upstream project releases it | Would retire accepted limitation 1 and remove the shared-password exposure |

## Rejected — recorded so they are not re-litigated

| ID | Item | Reason |
|---|---|---|
| X-01 | Two separate administrations, one per person | Two sets of books, no household view; defeats the purpose |
| X-02 | Switching to a different product for per-user roles | Considered when the limitation was found; rejected because the stated functional need is met |
| X-03 | Using CSV export as the backup mechanism | The vendor explicitly warns against it; recovery is a data-store backup |
| X-04 | Custom code, screens, or integrations on top of the product | Nothing to build that the product does not already do |
| X-05 | Exposing the instance to the internet as part of v1 | Not needed for a two-person home tool; would become B-04 with its own risk decision |
