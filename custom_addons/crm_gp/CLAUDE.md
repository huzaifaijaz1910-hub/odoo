# CLAUDE.md — crm_gp

Module-specific notes. Read `../../CLAUDE.md` first for workspace-wide setup.

## What this module is

GotaPura's six-stage CRM pipeline, built on Odoo CRM. Full requirements in
`../../GotaPura.md` — that brief is authoritative, and it explicitly says:
**if something isn't written there, don't invent it, ask.**

## Status

**Merged to main but NOT production ready.** 21 defects from manual testing.

| Document | What it's for |
|---|---|
| `../../crm_gp_defect_log.md` | What's broken, with evidence and brief references |
| `../../crm_gp_fix_brief.md` | Batched fix plan with sequencing |
| `../../crm_gp_manual_test_plan.md` | Phase-by-phase verification steps |

Read the defect log before changing anything here. Two systemic issues
(S-001, S-002) account for most of the defect list — fixing the numbered
defects individually produces patches that look right and don't work.

## Databases

| Name | Purpose |
|---|---|
| `crm_gp_final` | Clean install, used for verification. **Keep it clean.** |
| `crm_gp_verify` | Stage-progression testing. Contaminated with hand-edited dates, revenues and team assignments — don't trust its data. |

Iterate against `crm_gp_verify`, verify against a **fresh** database.

## Commands

```bash
# Iteration loop
odoo -c ~/odoo/odoo.conf -d crm_gp_verify -u crm_gp --stop-after-init

# Clean-install verification (what §14 requires)
dropdb crm_gp_check 2>/dev/null
odoo -c ~/odoo/odoo.conf -d crm_gp_check -i crm_gp --stop-after-init > /tmp/check.log 2>&1
grep -iE "ERROR|CRITICAL|Traceback" /tmp/check.log

# Browse
odoo -c ~/odoo/odoo.conf -d crm_gp_final --http-port=8071
```

## Testing this module specifically

**Create opportunities through the UI, not with SQL or the shell.** The
biggest defect class here is features that work when driven directly and are
unreachable when a salesperson creates a lead normally (D-001, D-013).

Known workarounds needed while S-002 is unfixed:
- New opportunities land on Odoo's **stock** New stage, not the module's.
  Click the correct stage chip manually (4th onward in the stage bar).
- New opportunities land on the stock **Sales** team, not GotaPura Sales.
  The escalation and quotation crons filter on team, so they match nothing
  until you set it by hand.

To test time-based behaviour, backdate an activity's `date_deadline` and run
the relevant cron manually from Settings → Technical → Scheduled Actions.

Note `crm_gp_escalation_level` on `mail.activity` tracks the highest level
reached and blocks re-firing. Reset it to test escalation twice on the same
record.

## Open questions

Eight decisions are pending client input — see the Open Questions section of
the defect log. The most blocking is **Q-1**: Odoo ships its own CRM stages
(four of them, including a Won at sequence 70) and lost reasons, and the
brief doesn't say whether to remove them. Don't decide this unilaterally.

## What's known good

Don't rewrite these — they pass every check against the brief:

- **§8 escalation chain** — all four levels, priority-tiered thresholds,
  level-3 summary content, revenue gating. The logic is sound; only the team
  filter (D-013) stops it firing.
- **§9 quotation validity** — correctly relies on Odoo's native
  `validity_date` / `is_expired` rather than reimplementing it.
- **§10 fair distribution** — native rule-based assignment with the Urgent
  exclusion correctly expressed as an assignment domain.
- **§11 monthly report** — all five required sections, scoped to the module's
  stages by external ID.
