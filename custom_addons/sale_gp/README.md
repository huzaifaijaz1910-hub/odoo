# sale_gp — GotaPura Sales

Odoo 19 module covering GotaPura's sales cycle from won opportunity through
quotation, order, delivery, invoice and payment. Companion to `crm_gp`, which
owns the CRM side, the tags, and quotation-validity rules that this module
reuses rather than duplicating.

Full specification: `docs/briefs/sale_gp.md`. Module-specific working notes:
`CLAUDE.md` in this directory.

## Status

Slice 1 of `docs/briefs/sale_gp.md` §15: module scaffold and the
stage-to-state mapping only. No shields, automations, tags, or dunning yet —
those land in later slices, in the order the brief lays out.

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

## Not in this slice (see brief §15 for order)

Tags, the five data-quality shields, sales-flow triggers, discount approval
tiers, the dunning ladder, reactivation alerts, and the monthly report.
Shield 4 (duplicate contract) additionally stays out of every slice until
the "what is a contract" question in brief §12 is answered.

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
