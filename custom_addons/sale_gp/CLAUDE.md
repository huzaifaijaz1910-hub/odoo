# sale_gp — Claude Code instructions

Odoo 19 Sales module for GotaPura. Data-quality shields plus sales-cycle triggers.

## Source of truth

`docs/briefs/sale_gp.md` is the specification. Read it before working on this module.

If something is not in the brief, **do not invent it — ask.** The brief has an open-questions
section (§12); those are genuinely undecided, not oversights. Leave a marked placeholder and
raise it. Never fill one in with a plausible-looking value.

Workspace setup, venv activation, the `odoo` commands and the verification standard are in the
root `CLAUDE.md`. Do not repeat them here or restate them in answers — read them from there.

## Repo boundaries

- Work on the `sale_gp` branch. Never commit to `main`.
- **Do not modify `custom_addons/crm_gp`.** It is merged to `main`, carries 21 documented
  defects, and is owned separately. `sale_gp` depends on it and reads from it, but never edits
  it. If a change there seems necessary, stop and ask.
- Do not modify `l10n_ao`, `zoom_tax_slab`, `bi_birthday_reminder` or `ai_claude`. They run the
  client's live system.
- The vendored Odoo source and `odoo.conf` are gitignored. Do not add them.

## Testing

Install and upgrade must both be clean on a fresh and an existing database, with no warnings in
the server log.

The five shields need manual testing against real failure cases before any is called done: an
email with no `@`, an email with a typo domain, a phone too short, a phone too long, a repeated
tax ID, an order invoiced twice, a vendor bill entered twice with the same reference and amount.

Follow the format of `crm_gp_manual_test_plan.md` for the test plan and `crm_gp_defect_log.md`
for anything found.

## Hard rules for this module

- **This module creates no `crm.tag` records.** `crm_gp` owns every tag. Reference them by
  external ID. There is no `data/sale_tags.xml` and there must not be one.
- **Quotation validity (15 days, D-3 reminder, D0 expiry) lives in `crm_gp`.** Do not
  reimplement it here.
- **The delivery booking email belongs to the Tasks module.** This module creates the delivery
  task; it does not send that email.
- **Do not build a custom stage model on `sale.order`.** The six stages map onto native `state`,
  `delivery_status` and `invoice_status` — see brief §3.
- **Do not build Shield 4 (duplicate contract) at all** until the "what is a contract" question
  in §12 is answered.
- Use native Odoo where it exists: `phone_validation` for phones, contact-merge for duplicates,
  `account_followup` for dunning. Do not hand-roll these.

## Blocks vs warnings

Only two things hard-block: invalid phone format, and a second invoice on an already-invoiced
order. Everything else warns and lets the user proceed with a justification. Do not turn a
warning into a block without asking me.

Anything that blocks must be overridable by a named security group and must state why it fired.

## Conventions

- Configuration goes in XML data files. Python only where logic cannot be expressed as config.
- Everything is namespaced `sale_gp` / `_gp` — external IDs, models, fields.
- Keep the client's V1–V16 rule numbers in external IDs and commit messages.
- Thresholds (discount tiers, dunning days, typo-domain list) are configuration settings, never
  literals in Python.
- Email templates: one record, English text, Portuguese via Odoo's translation mechanism. Never
  two records per language.

## Working style

- Work one slice at a time, following brief §15. Do not run ahead into later slices.
- Never push to `live` or `staging`. Feature branch, then a pull request.
- Update the module `README.md` as you go, not at the end.
- Anything assumed, skipped or left open goes in the "Open" section of the commit message.
