# sale_gp — GotaPura Sales

Odoo 19 module covering GotaPura's sales cycle from won opportunity through
quotation, order, delivery, invoice and payment. Companion to `crm_gp`, which
owns the CRM side, the tags, and quotation-validity rules that this module
reuses rather than duplicating.

Full specification: `docs/briefs/sale_gp.md`. Module-specific working notes:
`CLAUDE.md` in this directory.

## Status

Slice 1 (module scaffold, stage-to-state mapping) plus Shields 2 and 3 of
`docs/briefs/sale_gp.md` §6. No other shields, no triggers, no discount
tiers, no dunning yet — those land in later slices, in the order the brief
lays out.

## What's in this slice

- Module scaffold: manifest (declares the full dependency and data-file list
  per brief §2), folders, empty placeholder data/view files so the manifest
  loads cleanly.
- The six-stage sales cycle mapping (brief §3). Odoo's `sale.order` has no
  configurable stage model, so the six client-facing stages are derived from
  fields Odoo already tracks:

  | # | Stage | Colour | Odoo index | Driven by |
  |---|---|---|---|---|
  | 1 | Quotation | Grey | 8 | `state = draft` |
  | 2 | Sent | Blue | 4 | `state = sent` |
  | 3 | Negotiation | Orange | 2 | `state = sent` and a revision has been issued |
  | 4 | Confirmed | Cyan | 7 | `state = sale` |
  | 5 | Delivered | Blue | 4 | `delivery_status = full` |
  | 6 | Invoiced / Paid | Green | 10 | `invoice_status = invoiced`, payment state paid |

  Implemented on `sale.order` (`models/sale_order.py`):
  - `is_negotiation_gp` — stored boolean, set to `True` when
    `action_quotation_send` is called on an order already in `state = sent`
    (i.e. a revised quotation is being sent out after the first one).
  - `stage_gp` — computed, stored selection field reading the table above.
  - `color_gp` — computed, stored integer holding the matching kanban colour
    index, for use as a `color_field` once a kanban view is added.

  These fields are not yet surfaced in any view — that's UI wiring for a
  later slice.

## Shield 2 — wrong email (V2)

`res.partner`, warning only, never blocks.

- `models/res_partner.py`: `_email_gp_check(email)` flags a missing `@`, a
  missing domain, whitespace inside the address, or a domain that matches
  the typo list — and proposes a corrected address when one exists.
- `_onchange_email_gp` fires this while the user is editing the Email field
  and shows the result as a standard Odoo onchange warning popup
  (non-blocking — the value is not reverted).
- `email_gp_warning` is a computed field holding the same message, wired
  into the Contact form (`views/res_partner_views.xml`, inherits
  `base.view_partner_form`) as a small red note under the Email field, so
  the warning is still visible after the popup is dismissed.
- The typo-domain list is data, not a Python literal:
  `sale.gp.email.typo.domain` (`models/sale_gp_email_typo_domain.py`),
  seeded from `data/email_typo_domains_gp.xml`, editable at Sales →
  Configuration → Email Typo Domains (Sales Manager group).
  **Placeholder data** — the three seeded entries (`gmial.com`,
  `hotmial.com`, `yaho.com`) are the examples given in the brief itself.
  Brief §12 flags the real list as an open question; ask the client for
  their actual typo-domain history before relying on this in production.

## Shield 3 — wrong phone (V3)

`res.partner`, hard block — the only one of the five shields that blocks.

- `_check_phone_gp` (`@api.constrains('phone', 'country_id')`) runs
  `_phone_format(fname='phone', raise_exception=True)`, native to the
  `phone_validation` module this manifest already depends on. No
  hand-rolled regex: `phonenumbers` (via `phone_validation`) enforces
  Angola's `+244 9XX XXX XXX` mask and every other country's mask from the
  same call, based on the contact's `country_id` (falling back to the
  company's country).
  - `res.partner` in this Odoo build has no separate `mobile` field (only
    `phone`) — see root `CLAUDE.md` "Environment gotchas". The shield reads
    a `PHONE_FIELDS_GP` tuple defensively (`fname in partner._fields`) so it
    still validates `mobile` automatically if a future dependency adds the
    field back, without needing a code change here.
  - Too few or too many digits raises `ValidationError`, blocking the save.
- Overridable by the **Data Quality Shield Override** group
  (`security/security.xml`) per brief §13 ("anything that blocks... must be
  overridable by a named group"). Members of that group can save numbers
  Shield 3 would otherwise reject; everyone else gets a message stating
  which field, which number, and why it failed.

### `phonenumbers` must actually be installed

`phone_validation` depends on the `phonenumbers` PyPI package but degrades
**silently** without it — no error, every phone number is treated as valid,
and Shield 3 does nothing. Check for `pip show phonenumbers` /
`pip install phonenumbers` in the venv before trusting Shield 3 in any
environment. Logged in root `CLAUDE.md` "Environment gotchas" too.

## Not in this slice (see brief §15 for order)

Shields 1, 4 and 5, tags, sales-flow triggers, discount approval tiers, the
dunning ladder, reactivation alerts, and the monthly report. Shield 4
(duplicate contract) additionally stays out of every slice until the "what
is a contract" question in brief §12 is answered.

## How to test Shields 2 and 3 by hand

1. Install/upgrade, then open **Contacts** and create a new contact.
2. Type an email with a typo domain, e.g. `test@gmial.com`, then tab out of
   the field. A warning popup appears suggesting `test@gmail.com`; dismiss
   it and the value is unchanged — not blocked. The red note under the
   field repeats the warning until the email is fixed.
3. Type an email with no `@` (e.g. `test.example.com`) or no domain
   (e.g. `test@`) — same non-blocking warning behaviour, correction not
   always possible to propose.
4. Set Phone to something too short for the contact's country (e.g. `+244
   911` for an Angola contact) and save. The save is blocked with a message
   naming the field, the number, and why it failed.
5. Set Phone to something too long (e.g. `+244 923456789012345`) and save —
   same hard block.
6. Set Phone to a valid Angolan mobile (e.g. `+244 923 456 789`) and save —
   succeeds.
7. Add a user to the **Data Quality Shield Override** group (Settings →
   Users, or the group directly) and repeat step 4 as that user — the save
   now succeeds.

## How to test this slice by hand

1. Install: `odoo -c ~/odoo/odoo.conf -d <db> -i sale_gp --stop-after-init`.
   Check the log for `ERROR`, `CRITICAL`, `Traceback` — there should be none.
2. Open a database, create a quotation. Its `stage_gp` should read
   `quotation` and `color_gp` should be `8` (inspect via Settings → Technical
   → Database Structure → Fields, or the ORM shell — no view exposes them
   yet).
3. Send the quotation (state moves to `sent`). `stage_gp` becomes `sent`,
   `color_gp` becomes `4`, `is_negotiation_gp` stays `False`.
4. Send it again from the same `sent` state (a revision). `is_negotiation_gp`
   becomes `True`, `stage_gp` recomputes to `negotiation`, `color_gp` to `2`.
5. Confirm the order, validate the delivery, invoice and pay it, checking
   `stage_gp` / `color_gp` move to `confirmed` → `delivered` →
   `invoiced_paid` at each step.

## Open questions

Tracked in full in brief §12. Nothing in this slice depends on them.

**New, found while building this slice:** brief §3 drives stage 5
("Delivered") from `delivery_status`, but that field is defined by
`sale_stock`, which is not in the manifest's dependency list (brief §2 lists
`sale_management`, not `sale_stock`). The manifest was built exactly as
specified, so `sale_stock` was not added unilaterally. `_get_stage_gp` reads
`delivery_status` defensively (`"delivery_status" in self._fields`) so the
module installs cleanly without it — but as a consequence, `stage_gp` can
currently reach `confirmed` and never `delivered`. Needs a decision: either
add `sale_stock` to `depends`, or point "Delivered" at a different signal.
