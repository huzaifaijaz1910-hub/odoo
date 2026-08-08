# GotaPura CRM (`crm_gp`)

Turns Odoo CRM into GotaPura's seven-stage sales pipeline (enquiry to signed
installation). Full brief: `../GotaPura.md`.

## Status: three slices in

Per the brief's suggested order of work (section 15):

- Module scaffold and manifest.
- The six pipeline stages.
- The ten CRM tags (priority + segmentation).
- The five mandatory lost reasons.
- Fair lead distribution configuration (native Rule-Based Assignment).
- Stage automations that create activities (the computable subset - see
  below).
- Quotation validity: 15 day default, automatic expiry, 3-day-before
  reminder (see below).

**Deliberately skipped, not forgotten** (brief section 7): all ten
email templates. Section 7 says the client will paste the exact approved
English wording and that templates must be "written against what is
written here, not from your own drafting." No approved wording exists yet
in the brief, so no `mail.template` records are created rather than
guessing at marketing copy. Once wording is provided, add
`data/mail_templates.xml` and wire the "send email" actions into the stage
automations below.

**Not yet built** (later slices, per the brief): the courtesy/lost email
and the monthly performance report (see below for why).

### Escalation chain (brief section 8) - not built, needs a decision first

Two separate blockers, surfaced and confirmed with the client rather than
worked around silently:

- **Timing precision isn't achievable as specified.** Level 1's delays are
  hour-based (Urgent +4h, High +24h, Medium/Low +48h), counted from an
  activity's due date. `mail.activity.date_deadline` is a `Date` field
  with no time-of-day component - activities are day-granular everywhere
  in Odoo, not a limitation specific to this rule. Rounding to whole days
  (as done for the stage activities) would make "respond within 4 hours"
  and "respond within 24 hours" indistinguishable, defeating the point of
  the tiered urgency. Real hour-level timing needs a custom datetime field
  tracking "became overdue at," which is a bigger design commitment than a
  config tweak.
- **Levels 2-4 name people who aren't identified yet** (brief section 12):
  the backup salesperson (level 2), the team supervisor (level 3), and
  who counts as general management (level 4). Can't wire up "notify X"
  without knowing who X is.

Confirmed with the client to skip this slice entirely for now rather than
build something that doesn't match the tiering, or guess at recipients.

### Monthly performance report (brief section 11) - not built

Same recipient problem as escalation level 4: "send management a
performance summary" needs a management recipient, which is on the same
unresolved list (section 12). On top of that, one of the requested
figures - "average days spent in each stage" - isn't backed by any
existing field; Odoo doesn't track stage-transition history out of the
box, so getting it means designing a way to log stage changes with
timestamps first. Flagging both rather than shipping a report with a
guessed recipient or a fudged duration metric.

### Quotation validity (`data/quotation_validity.xml`)

Brief section 9. Expiry itself needed no automation: Odoo already computes
`sale.order.validity_date` from `company.quotation_validity_days` and
flags a draft/sent order `is_expired` once that date passes, which is the
"expires automatically" behaviour the brief asks for - this file just sets
the company default to 15 days. This is company-wide because the database
looks like a single-company (GotaPura) instance; flag it if that turns out
to be wrong.

The "reminder 3 days before expiry" isn't one of the ten templates in
section 7, so it's implemented as an internal to-do activity for the
quotation's salesperson (not a customer email) via a daily cron scoped to
quotations on the GotaPura Sales team - flag if the client actually meant
a customer-facing reminder instead. Tested for both firing correctly and
not duplicating on a second run the same day.

## What this installs

### Pipeline stages (`data/crm_stages.xml`)

Six sequential `crm.stage` records, sequence 10-60: New, Qualified,
Technical Survey, Proposal, Negotiation, Won (`is_won = True`). "Lost" is
deliberately not a stage — use the native "Mark as Lost" button on the
opportunity, which already requires a lost reason.

### Lost reasons (`data/crm_lost_reasons.xml`)

Price, Competition, No response, Postponed, Out of scope.

### Tags (`data/crm_tags.xml`)

Ten `crm.tag` records (priority: Urgent/High/Medium/Low; segmentation:
Residential/Business/On site Survey/Online Survey/Reactivation 90d/Overdue).

The brief specified a colour index per tag, "verify each index against the
live Odoo 19 palette... the colour name wins, the index is my best
reading." Checked against
`odoo/addons/web/static/src/core/colorlist/colorlist.js`
(0 No color, 1 Red, 2 Orange, 3 Yellow, 4 Cyan, 5 Purple, 6 Almond, 7 Teal,
8 Blue, 9 Raspberry, 10 Green, 11 Violet) and corrected three mismatches:

| Tag | Brief said | Corrected to | Why |
| :--- | :--- | :--- | :--- |
| Residential | 4 (actually Cyan) | 8 (Blue) | brief named the colour "Blue" |
| Business | 6 (actually Almond) | 5 (Purple) | brief named the colour "Purple" |
| Online Survey | 7 (actually Teal) | 4 (Cyan) | brief named the colour "Cyan" |

Two more tags name a colour that doesn't exist in the Odoo 19 palette at
all. Left as placeholders — **flagging for client confirmation, not
guessing a final answer**:

- **On site Survey** — brief says "Dark blue"; no such colour exists.
  Using Violet (11) as a placeholder so it's visually distinct from
  Residential's Blue.
- **Reactivation 90d** — brief says "Grey"; no such colour exists. Using
  "No color" (0), which renders as a neutral grey pill.

### Fair lead distribution (`data/crm_team_assignment.xml`)

Per section 10, this uses Odoo's native Rule-Based Assignment rather than
custom code. A dedicated `GotaPura Sales` team (`crm.team`) is created
(instead of reconfiguring the stock "Sales" team) so this stays namespaced
and doesn't disturb whatever that team is already used for. Its
`assignment_domain` excludes anything tagged Urgent, since the brief
requires urgent leads to be assigned manually by the supervisor. The daily
`CRM: Lead Assignment` cron (`crm.ir_cron_crm_lead_assign`) is activated.

**Not configured, because the answer isn't known yet** (brief section 12):
no `crm.team.member` records are created under this team. Once the real
sales team roster is confirmed, add one `crm.team.member` per salesperson
under "GotaPura Sales" with `assignment_max` starting at 15-20, and toggle
`assignment_optout` for anyone away on holiday/sick leave (there is no
automatic holiday-calendar integration here — `hr_holidays` is not a
dependency of this module).

### Stage automations (`data/automation_rules.xml`, `data/activity_types.xml`)

Native Automation Rules (`base.automation`), one per stage, triggered on
"Stage is set to" and using the built-in "Create Next Activity" server
action - no Python needed for these, plus one small `code` action for the
Lost tag/activity. Stage-entry activities (created the moment the lead
enters the stage):

| Stage | Activities automated on entry |
| :--- | :--- |
| New | Contact the lead (1d, Call), Validate contact details (1d, To-Do), Apply initial tags (0d, To-Do) |
| Qualified | Schedule the survey (2d, To-Do), Record qualification notes (0d, To-Do), Second phone follow up (3d, Call) |
| Technical Survey | Carry out the survey (5d) |
| Proposal | Prepare and send the proposal (3d) |
| Negotiation | Negotiation meeting or call (2d) |
| Won | Prepare and send the contract (1d), Schedule the installation (5d), Welcome call (2d) |
| Lost (lost reason set, i.e. "Mark as Lost") | Reactivation activity (90d, To-Do), auto-apply "Reactivation 90d" tag |

On top of that, the activities whose due date depends on a **previous
activity being marked done** (not stage-entry time) are wired up using
Odoo's native activity chaining
(`mail.activity.type.chaining_type`/`triggered_next_type_id`, defined in
`data/activity_types.xml`) - marking one done automatically schedules the
next, with its due date computed from the completion date. Pure
configuration, tested end-to-end by marking each activity done and
confirming the next one appears with the right due date:

| Completing... | ...auto-creates | Due |
| :--- | :--- | :--- |
| Carry out the survey | Issue the technical report | +2 days |
| Prepare and send the proposal | Proposal follow up | +3 days |
| Proposal follow up | Second follow up | +4 days later |
| Negotiation meeting or call | Issue revised proposal | +1 day |
| Issue revised proposal | Periodic follow up | +2 days |
| Periodic follow up | Periodic follow up (again) | +2 days, repeats |

These use dedicated `GP:`-prefixed activity types instead of the generic
Call/To-Do/Meeting types, because chaining is a property of the *type*,
which is global - putting it on the generic "To-Do" type would make every
unrelated use of "To-Do" anywhere in this database auto-chain into a
GotaPura follow-up.

Five mechanical notes/approximations, all called out in the XML files:

- The Lost rule triggers on `lost_reason_id` going from unset to set
  (`on_write` + `filter_pre_domain`/`filter_domain`), not on archive. "Mark
  as Lost" (`action_set_lost`) archives the record first and sets the lost
  reason in a separate call, so an `on_archive` trigger would fire too
  early, before there's a reason to check.
- The Lost rule's activity + tag are done via one `code` action, not the
  declarative "Create Next Activity" action. The built-in action silently
  no-ops here: `action_set_lost()` writes `lost_reason_id` together with
  `probability`/`automated_probability` in the same call, and the built-in
  action's `_is_recompute()` guard (meant to stop duplicate activities when
  a write is just a recompute side-effect) mistakes that combined write for
  one and skips creating the activity. Confirmed by testing both ways
  end-to-end before settling on the `code` version.
- The built-in activity action only supports day/week/month granularity,
  so the brief's hour-level due dates are rounded to the nearest day
  (24h -> 1 day, 48h -> 2 days). "Business days" are approximated as
  calendar days.
- "Second phone follow up on day 3 if no reply" (Qualified) is created
  unconditionally rather than skipped: detecting "no reply" needs inbound
  email tracking, which is out of scope, and an occasionally-unnecessary
  reminder is harmless, unlike a missing one.
- "Confirm missing data" (Technical Survey, "only if applicable") is
  **not** automated - explicitly conditional on a judgement call
  (incomplete survey form), where creating it unconditionally would be
  actively wrong rather than just redundant. Left to the salesperson.
- The two Proposal follow-ups are both specified as "N days after
  sending", but native chaining can only go send -> follow up 1 -> follow
  up 2 sequentially, so follow up 2's timing drifts from a fixed "7 days
  after sending" to "4 days after follow up 1 is completed" if that
  isn't completed exactly on its due date.
- "Periodic follow up every 2-3 days" (Negotiation) is approximated as a
  fixed 2 days via self-chaining (a type chaining to itself), since
  chaining only supports one fixed delay. It keeps respawning for as long
  as someone keeps marking each one done - it has no awareness of the
  lead leaving the Negotiation stage, so a stray one can outlive the
  stage. Flagging this rather than building stage-aware auto-cancellation.

## Open questions carried over from the brief (section 12)

Not resolved by this slice, and nothing here should be read as an answer
to them:

- Technical survey form link (Qualified stage email — not yet built).
- On site survey fee amount, and whether it varies by region.
- Expected revenue threshold for level 4 escalation (medium/low priority).
- Who the backup salesperson is at escalation level 2.
- Exact sales team structure: salespeople, supervisor, general management.

## How to test by hand

1. Install `crm_gp` on a fresh database (or `-u crm_gp` to upgrade).
2. CRM > Configuration > Stages: confirm the six GotaPura stages appear in
   that order, and that a lead moved to "Won" is treated as won.
3. CRM > Configuration > Tags: confirm all ten tags and colours.
4. CRM > Configuration > Lost Reasons: confirm the five reasons; try
   "Mark as Lost" on an opportunity and confirm a reason is required.
5. CRM > Configuration > Sales Teams: open "GotaPura Sales", confirm
   "Assignment Domain" excludes the Urgent tag, and that Settings >
   Technical > Scheduled Actions > "CRM: Lead Assignment" is active.
6. Settings > Technical > Automation Rules: confirm the seven `crm_gp:`
   rules (one per stage plus Lost) and that each shows the right activities
   under its Actions tab.
7. Create an opportunity, move it through the stages one at a time, and
   confirm the matching activities appear on it each time with the right
   due dates and assignee (the opportunity's salesperson). Mark it lost
   with a reason and confirm the "Reactivate lead" activity (due in 90
   days) is created and the "Reactivation 90d" tag is applied.
8. On an opportunity in Technical Survey, Proposal or Negotiation, mark
   each stage's first activity ("Carry out the survey" / "Prepare and
   send the proposal" / "Negotiation meeting or call") done one at a time
   and confirm the next activity in that chain appears automatically with
   the right due date (see the chaining table above). In Negotiation,
   confirm marking "Periodic follow up" done creates another one.
