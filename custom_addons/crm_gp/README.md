# GotaPura CRM (`crm_gp`)

Turns Odoo CRM into GotaPura's seven-stage sales pipeline (enquiry to signed
installation). Full brief: `../GotaPura.md`.

## Status: six slices in - every brief section built

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
- Four-level overdue escalation chain (brief section 8 - see below).
- Monthly performance report (brief section 11 - see below).
- Email templates, wired into the automations above (brief section 7 -
  see below).

**Nothing left unbuilt in the brief.** The one thing genuinely
unfinished - the ten templates' actual wording - isn't an engineering
gap: the brief explicitly withholds it ("I will paste the exact English
text... write against what is written here, not from your own
drafting") and forbids drafting it ahead of time. See below for what
*is* built around that gap, and exactly what's left for the client to
drop in.

### Email templates (brief section 7) - infrastructure built, wording pending

All ten `mail.template` records exist (`data/mail_templates.xml`), fully
wired into the automations that should send each one, with every body
holding the literal placeholder `[PENDING CLIENT WORDING - EN]` (and
`[PENDING CLIENT WORDING - PT]` in the Portuguese translation) instead of
invented copy. **When the client supplies real text, only the
`body_html` field on each template needs replacing** - everything else
(model, subject, recipient resolution, language selection, wiring) is
already correct:

| # | Template | Subject | Sent when |
| :-- | :-- | :-- | :-- |
| 1 | New | "We have received your enquiry" | Immediately on entering New |
| 2 | Qualified | "Next step: technical survey for your solution" | 4h after entering Qualified |
| 3 | Technical Survey | "Technical survey confirmed" | Immediately on entering the stage |
| 4 | Proposal | "Your GotaPura proposal — {{ object.name }}" | Not auto-sent - see below |
| 5 | Negotiation | "Following up on your proposal" | Immediately on entering the stage |
| 6 | Won | "Welcome to GotaPura — award confirmation" | Immediately on entering the stage |
| 7 | Lost | "Thank you for your time" | Immediately when marked lost |
| 8 | Escalation L2 | "...backup follow-up needed..." | Escalation level 2 (brief §8) |
| 9 | Escalation L3 | "...supervisor review needed..." | Escalation level 3 |
| 10 | Escalation L4 | "...opportunity overdue..." | Escalation level 4 |

Subjects 1-3, 5-7 are the brief's own wording verbatim; the Proposal
subject uses the brief's `{{ }}` placeholder syntax for the reference.
Subjects 8-10 aren't given in the brief (only body content is described
for escalation notices, and only for level 3's supervisor summary), so
those are functional labels I wrote, not approval-gated client copy like
the rest - flag if the client wants those worded/approved too.

**Proposal (#4) is deliberately not auto-sent** on stage entry: the
proposal itself is prepared by the salesperson (the "Prepare and send the
proposal" activity, up to 3 business days after entering the stage), so
it isn't ready to send the moment the stage changes. Instead it's
attached as a suggested template on that activity type
(`mail_template_ids`), one click away for the salesperson when they
actually send it.

**Escalation levels 2-4** (#8-10) previously only created activities and
followers; now each also sends its templated email to the relevant
person (backup salesperson / supervisor / management), resolved from the
same `ir.config_parameter` placeholders as before
(`data/escalation_chain.xml`).

**Technical setup that's already correct, ready for real copy:**

- **Recipient**: the seven customer-facing templates use
  `use_default_to=True`, so the lead's own partner/email is the
  recipient - never hardcoded. The three escalation templates leave the
  recipient unset in the template itself; the escalation code resolves it
  from the `ir.config_parameter` placeholders and passes it at send time.
- **Language**: `lang` on the customer-facing templates is
  `{{ object.lang_id.code or object.partner_id.lang or 'en_US' }}`, so a
  Portuguese-speaking customer's lead automatically gets the Portuguese
  translation - verified end-to-end on a disposable database with
  `pt_AO` installed as a language: a lead for a customer with
  `lang='pt_AO'` correctly received the Portuguese placeholder subject
  and body, not the English default.
- **Portuguese translation** (`i18n/pt_AO.po`): same placeholder pattern,
  loaded through Odoo's standard translation mechanism (per brief section
  7 - "loaded through Odoo's standard translation mechanism... do not
  create two separate template records per language"), not separate
  template records. **Locale chosen as `pt_AO` (Angola)**, not `pt_PT` or
  `pt_BR` - Odoo has no bare "pt" code, and this database's other custom
  addon is `l10n_ao`. Flag with the client if a different Portuguese
  variant is actually wanted. All ten templates currently share the
  identical placeholder body, so the `.po` file has one consolidated
  `msgid`/`msgstr` pair covering all ten locations rather than repeating
  it - **once real (and differing) copy lands, that entry will need
  splitting back into one per template**.
- Once real wording exists, apply the brief's remaining rules when
  writing it in: every template ends with sign-off "The GotaPura Sales
  Team"; the strapline "Where your water is our priority" goes on the
  first and last templates in the journey (tentatively New and Won here -
  the successful-journey reading - vs. New and Lost if "the journey"
  means the literal order in section 6; confirm with the client); plain,
  warm, professional, short paragraphs, no marketing language; every
  dynamic value uses `{{ object.partner_id.name }}`-style placeholders,
  never hardcoded.

**A bug worth knowing about, found and fixed while wiring this in**: the
same `_is_recompute()` false-positive documented below for the Lost
reactivation activity *also* affects the declarative "Send Email" action,
not just "Create Next Activity" - confirmed by testing (the courtesy
email silently produced no `mail.mail` until switched to a `code` action
calling `template.send_mail()` directly, same fix pattern as before).

### Escalation chain (brief section 8)

Built as an hourly `ir.cron` (`crm_gp_cron_escalation` in
`data/escalation_chain.xml`, logic in
`models/crm_lead.py::_cron_gp_process_overdue_escalations`), not a
`base.automation` time-based trigger, for a specific reason: the timing
thresholds are hour-level (Urgent +4h, High +24h, Medium/Low +48h, etc.)
but `mail.activity.date_deadline` is a `Date` field with no time-of-day
component - activities are day-granular everywhere in Odoo. Running an
hourly cron and computing "hours overdue" in Python (counted from
midnight after the due date - see the model for the exact math) gets
real hour precision without needing a custom datetime field on every
activity.

A small model extension backs this (`models/mail_activity.py`): one
Integer field, `crm_gp_escalation_level`, added to `mail.activity`
itself rather than to the lead. That's what makes the cron idempotent
and self-resetting for free - the field lives on the specific overdue
activity, so a fresh activity (stage change or chaining) always starts
at level 0, with no explicit reset logic needed.

Per level: 1 applies the "Overdue" tag and posts a chatter reminder to
the assigned salesperson; 2 subscribes a backup salesperson as a follower
and gives them their own activity (original ownership untouched); 3
gives the supervisor a summary activity with stage, expected value, days
overdue and last contact (approximated as the most recent chatter message
- the brief doesn't define "last contact" more precisely than that); 4
sends an actual internal email to management, skipped for medium/low
priority leads under the configured revenue threshold. Level 4's email
is a short factual system notification generated in code, not a
`mail.template` - deliberately kept out of the ten pending templates,
since it's an operational alert, not client-facing copy needing approval.

**The three people the brief leaves unidentified** (backup salesperson,
supervisor, general management - section 12) are `ir.config_parameter`
entries, not hardcoded: `crm_gp.escalation_l2_backup_user_id`,
`crm_gp.escalation_l3_supervisor_user_id`,
`crm_gp.escalation_l4_management_user_id`, each a `res.users` id,
defaulting to the admin user as a placeholder. **Set the real people
under Settings > Technical > Parameters > System Parameters before this
goes near production** - until then every escalation lands on whoever
installed the module. Same treatment for the level 4 revenue threshold
(`crm_gp.escalation_l4_revenue_threshold`, brief: "make the threshold a
configuration setting rather than a hardcoded number"), defaulting to
`0.0` - i.e. not filtering anything until a real number is set.

Tested end-to-end on a disposable database: a High-priority lead backdated
to ~30-36h overdue stopped correctly at level 1 only; an Urgent lead
backdated 5 days overdue cascaded through all 4 levels in one cron pass
(tag, backup activity + follower, supervisor activity, and - once a
recipient email was configured - the management email with the right
subject/recipient); running the cron twice produced no duplicate
activities or emails.

### Monthly performance report (brief section 11)

Built as a monthly `ir.cron` (`crm_gp_cron_monthly_report` in
`data/monthly_report.xml`, `nextcall` computed to land on the 1st of next
month, logic in `models/monthly_report.py`), sending an HTML email
covering everything the brief asks for: leads by source, conversion rate
per stage, average days spent in each stage, won/lost counts with lost
reasons broken down, and performance per salesperson. Covers the calendar
month that just ended, for opportunities on the GotaPura Sales team.

The recipient ("send management a performance summary") is
`crm_gp.monthly_report_recipient_user_id`, an `ir.config_parameter`
defaulting to the admin placeholder - same pattern as the escalation
chain's three unresolved people, rather than blocking on the brief's
undefined "management". **Set the real recipient under Settings >
Technical > Parameters before relying on this.**

Stage-duration data comes from crm.lead's native `duration_tracking`
field (`mail.tracking.duration.mixin`, driven by crm.lead's
`_track_duration_field = 'stage_id'`) - the same `mail.tracking.value`
history crm's own stage-duration/rotting features are built on, not a
bespoke tracking table. "Conversion rate per stage" is the percentage of
this month's new leads whose `duration_tracking` contains an entry for
that stage (i.e. they spent any time there, however brief); "average days
per stage" averages actual seconds spent (including a genuine 0 for a
same-instant transition) over leads that have an entry for that stage,
converted to days.

Two cohort/scope decisions worth knowing about, since the brief doesn't
spell out the exact windowing:

- **"Leads by source" and "conversion rate"** use opportunities *created*
  in the reporting month.
- **"Average days per stage" and "won/lost"** use a wider cohort: that
  same set, plus any opportunity created earlier that was *won or lost*
  during the reporting month - so a deal that closes this month still
  shows up in this month's report even if it originated earlier.

Verified end-to-end on a disposable database with hand-backdated leads
(one created 25 days ago that moved New -> Qualified -> Won, one lost,
one still open): every figure in the generated report - reached-counts,
conversion percentages, per-stage average days, won/lost counts and
revenue, lost reason breakdown, and per-salesperson stats - matched
hand-computed expected values exactly.

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
6. Settings > Technical > Automation Rules: confirm the `crm_gp:` rules
   (one per stage plus Lost plus the delayed Qualified email) and that
   each shows the right activities/actions under its Actions tab.
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
9. Settings > Technical > Parameters > System Parameters: confirm the four
   `crm_gp.escalation_*` parameters exist, then set the three user-id ones
   to real people before relying on this in anything resembling
   production. Settings > Technical > Scheduled Actions: confirm
   "crm_gp: Overdue escalation chain" is active, hourly. To test without
   waiting a real 4+ hours, backdate an activity's due date a few days
   into the past on a tagged opportunity (Urgent/High/no tag), then run
   `env['crm.lead']._cron_gp_process_overdue_escalations()` from `odoo
   shell` and confirm the Overdue tag, backup activity, supervisor
   activity and (with a recipient email configured) the management email
   appear as expected for how overdue it is.
10. Settings > Technical > Parameters > System Parameters: confirm
    `crm_gp.monthly_report_recipient_user_id` exists, then set it to the
    real recipient. Settings > Technical > Scheduled Actions: confirm
    "crm_gp: Monthly performance report" is active, monthly, and its
    "Next Execution Date" lands on the 1st of a month. To test without
    waiting, run `env['crm.lead']._cron_gp_send_monthly_report()` from
    `odoo shell` (with a recipient email configured) and check the
    generated `mail.mail` record's body against opportunities you'd
    expect to see for last month.
11. Settings > Technical > Email > Templates: confirm all ten `GotaPura
    CRM:` templates exist with the placeholder body. Create an
    opportunity for a partner and confirm the "We have received your
    enquiry" email is queued (Settings > Technical > Email > Emails);
    move it to Technical Survey/Negotiation/Won/Lost and confirm each
    stage's email queues too. Set a partner's language to Portuguese
    (Angola) and confirm the queued email's subject/body switch to the
    `[PENDING CLIENT WORDING - PT]` placeholder instead of English (needs
    Portuguese (Angola) activated under Settings > Translations >
    Languages first).
