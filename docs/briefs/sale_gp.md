Sales Technical Brief — module `sale_gp`

**Module name:** `sale_gp`. All questions on this brief come to me.

This document is the single source of truth for the Sales work. If something is not written here, do not invent it. Ask.

This brief is the companion to the CRM brief (`crm_gp`). Where the two overlap — tags, colours, quotation validity, monthly reporting — the CRM brief wins and this module reuses its records rather than creating its own.

1. What this module does

GotaPura sell and install water treatment systems. The CRM module carries an enquiry to a won opportunity. This module takes it from there: quotation, order, delivery, invoice, payment.

It does two jobs at once.

The first is **data quality**. Five automatic shields that stop bad data entering at source: duplicate contacts, malformed emails, malformed phone numbers, a second contract for a client who already has one, and a second invoice for an order already invoiced.

The second is the **sales flow with triggers**. From quotation to payment, with follow-ups, quotation expiry, tiered discount approval, automatic dunning of overdue invoices and a credit block on clients who do not settle.

The system is used by Portuguese speakers. Every customer facing email must exist in Portuguese and English.

2. Module identity

Create the module at the repository root as `sale_gp`.

Manifest must declare exactly this:

```python
{
    "name": "GotaPura Sales",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "summary": "Five data-quality shields, sales-cycle triggers, discount approvals and escalating dunning",
    "author": "Supply Steer Technologies",
    "website": "https://supplysteer.com",
    "license": "Other proprietary",
    "depends": [
        "sale_management",
        "account",
        "contacts",
        "mail",
        "phone_validation",
        "project",
        "crm_gp",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_templates.xml",
        "data/automation_rules.xml",
        "data/ir_cron.xml",
        "views/res_config_settings_views.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
```

`crm_gp` is a hard dependency because the tags and colours live there and are inherited through to the order and the invoice. If the tags end up owned by this module instead, tell me before you change the dependency.

Folder layout:

```
sale_gp/
├── __init__.py
├── __manifest__.py
├── README.md
├── data/
├── models/
├── security/
└── views/
```

3. The six-stage sales cycle

The client's specification describes six stages. **Odoo `sale.order` has no configurable stage model** — it has `state` (draft, sent, sale, cancel) plus delivery and invoice status. Do not build a custom stage model. Map the six stages onto what Odoo already tracks:

| # | Stage | Colour | Odoo index | Driven by |
| :---- | :---- | :---- | :---- | :---- |
| 1 | Quotation | Grey | 8 | `state = draft` |
| 2 | Sent | Blue | 4 | `state = sent` |
| 3 | Negotiation | Orange | 2 | `state = sent` and a revision has been issued |
| 4 | Confirmed | Cyan | 7 | `state = sale` |
| 5 | Delivered | Blue | 4 | `delivery_status = full` |
| 6 | Invoiced / Paid | Green | 10 | `invoice_status = invoiced`, payment state paid |

Negotiation is the only one with no native equivalent. Add a stored boolean `is_negotiation_gp` on `sale.order`, set when a revised quotation is issued after the first send, and drive the kanban colour from a computed field that reads the table above. Do not add a second workflow alongside Odoo's.

4. Tags and colours

Eight business tags as `crm.tag` records, reused on `sale.order` and inherited onto the invoice. Colour indices must match the CRM brief, because the same palette runs across every module on this project.

**`crm_gp` owns every tag record. This module creates none.** There is no `data/sale_tags.xml` and there must not be one. Reference the tags by their `crm_gp` external ID. Creating a second set of records with the same names is the failure this rule exists to prevent: the tags would look correct in both modules while the CRM → quotation → order → invoice inheritance silently splits across two sets, and reporting by business line — the entire reason the tags exist — comes out wrong without anything raising an error. If a tag you need is missing, add it to `crm_gp` and tell me.

| Tag | Colour | Odoo index | Used for |
| :---- | :---- | :---- | :---- |
| 20L Bottles | Blue | 4 | Bottled water, refill rounds. |
| Point of Use | Cyan | 7 | Under-sink and countertop units. |
| Equipment | Purple | 6 | Hardware sales, filters, pumps, tanks. |
| Monthly Contract | Green | 10 | Recurring supply or maintenance contract. |
| Key Accounts | Yellow | 3 | Named large clients. |
| Export | Dark purple | 6 | Orders shipped outside Angola. |
| Urgent | Red | 1 | Immediate action, under 4 hours. |
| Renewal | Orange | 2 | Applied automatically to orders generated from a recurring monthly contract. |

Verify each index against the live Odoo 19 palette before committing and correct any that do not match the colour named. The colour name wins, the index is my best reading.

Export and Equipment are both reading as purple in the client's artwork. Confirm with me which index Export takes before you commit — see section 12.

Tags flow CRM opportunity → quotation → sale order → invoice. That inheritance is the whole point: it is what makes reporting by business line work without anyone tagging anything twice.

5. Default activities

Four activity types, created on the order and assigned to the salesperson.

| Activity | Trigger | Due |
| :---- | :---- | :---- |
| Quote follow-up | Quotation sent, no reply | 3 days after sending |
| Negotiation call | Order enters Negotiation | 2 days |
| Confirm delivery with client | Order confirmed | Same day |
| Payment collection | Invoice overdue | See the dunning ladder, section 8 |

6. Automation 1 — the five data-quality shields

This is the half of the module that has to be right first time, because it changes what users are allowed to save.

**Shield 1 — Duplicate contact**

On saving a `res.partner`, compare phone, mobile, email and tax ID (VAT) against the existing base.

On a match, show a warning naming the existing record — "This number already belongs to [Client X]" — with a link to it. The user then either reuses the existing record or writes a justification to proceed. This is a **warning, not a block**: legitimate cases exist, such as two contacts at one company sharing a switchboard number.

Use Odoo's native contact-merge feature plus rules on `res.partner`. Do not write a bespoke deduplication engine.

**Shield 2 — Wrong email**

Validate format on the field itself: missing `@`, missing domain, whitespace inside the address, and a maintained list of common typo domains — `gmial.com`, `hotmial.com`, `yaho.com` and the rest.

On failure the field turns red and suggests the correction. Warning, not a block.

The typo domain list must be **configuration, not a Python literal**. Put it in a data file so the client can extend it without a code change.

**Shield 3 — Wrong phone**

Angolan mask `+244 9XX XXX XXX`, with per-country international validation for everything else.

Use Odoo's native `phone_validation` module. Do not hand-roll regex per country.

Too few or too many digits **block the save** with a warning. This is the one shield that is a hard block, because a phone number that does not dial is worthless and there is no legitimate exception.

**Shield 4 — Duplicate contract**

Before confirming an order carrying the "Monthly Contract" tag, search for active contracts against the same tax ID or phone.

If one exists, notify the salesperson and the sales manager. Warning, not a block — a client can genuinely hold two contracts for two sites.

"Active contract" needs defining against a real Odoo object before you build this. See section 12.

**Shield 5 — Duplicate invoice**

Two halves.

- **Customer invoices:** an order already fully invoiced cannot generate a second invoice. Hard block. Exceptions require a recorded Finance approval, written to the chatter.
- **Vendor bills:** same vendor reference with the same amount raises a possible-duplicate alert to Finance. Warning, not a block.

**Initial clean-up**

Before the shields go live, run a one-off hygiene pass over the existing base: merge duplicates, fix invalid emails and phones. Switching the shields on over dirty data means every existing record starts throwing warnings on the first edit and the team learns to ignore them.

This clean-up is a **data operation, not part of the module**. Ship it as a script under `tools/` with a dry-run mode that reports what it would change before anything is written. Nothing runs against live data without me seeing the dry-run output first.

7. Automation 2 — sales flow triggers

| Trigger | Condition | Action |
| :---- | :---- | :---- |
| Won opportunity | CRM opportunity marked Won | Quotation created in one click, tags carried over |
| Quotation sent | No reply after 3 days | Follow-up activity for the salesperson, friendly email to the client |
| Quotation validity | D-3 before expiry | Expiry reminder to the salesperson |
| Quotation validity | D0 | Quotation expires automatically |
| Order confirmed | — | Creates the delivery task in the Tasks module, which fires its own booking email to the client |
| Delivery validated | — | Invoice generated and sent to the client |
| Client inactive | No purchase in 60 days | Reactivation alert to the salesperson |

Quotation validity is 15 days, driven from `validity_date`. This is the same rule as section 9 of the CRM brief — **implement it once**, in `crm_gp`, and do not duplicate it here.

The delivery task creation writes into the Tasks module. Do not send the booking email from this module; the Tasks module owns that email and sending it from both means the client gets it twice.

8. Discount approval tiers

Applied on the order line and on the order total.

| Discount | Approver |
| :---- | :---- |
| Up to 10% | Salesperson decides, no approval |
| Over 10% up to 20% | Sales Manager |
| Above 20% | General Director |

Confirmation is blocked while approval is pending. Approval happens inside Odoo and is written to the chatter — who approved, what percentage, when. No approvals by WhatsApp.

Make the two thresholds configuration settings, not hardcoded numbers.

9. Dunning ladder

Counted from the invoice due date, on a daily cron.

| Level | Day | Action | Recipient |
| :---- | :---- | :---- | :---- |
| 1 | D+3 | Friendly reminder | Client |
| 2 | D+7 | Second notice | Client, salesperson notified |
| 3 | D+15 | Formal letter | Client, Manager and General Director alerted |
| 4 | D+15 | Block the client for new credit orders until settled | Salesperson notified |

The credit block is the only irreversible-feeling step here, so it must be visible on the partner record and manually liftable by someone with the right group. Do not make it silent.

Use Odoo's native follow-up (`account_followup`) levels where they fit rather than writing three cron jobs by hand.

10. Reports and KPIs

Monthly, on day 1, as a scheduled action.

| KPI | Detail |
| :---- | :---- |
| Sales by salesperson and by tag | Ranking, with prior-month comparison |
| Quote → order conversion rate | By salesperson and by business line |
| Average days to payment | By client. Feeds the credit blocking decision |
| Quotes expired unanswered | Lost reason mandatory |
| Top 10 clients, and clients at risk | No purchase in 60 days |
| Data quality | Duplicates caught, emails and phones corrected |

The client wants the Sales, Tasks, HR, Payroll and Marketing monthly reports to arrive as **one consolidated email**, not five. Build this report so it can be called by a consolidator rather than sending on its own — a method that returns its section, with the sending left to whichever module owns the consolidated mail. Which module that is has not been decided. See section 12.

11. Rule reference — V1 to V16

The client's specification numbers the rules. Keep these identifiers in the external IDs and in commit messages so their document and our code can be read side by side.

| # | Trigger | Condition | Action | Recipient |
| :---- | :---- | :---- | :---- | :---- |
| V1 | Save contact | Phone, email or tax ID exists | Warning + link to original | User |
| V2 | Edit email field | No `@`, no domain, typo | Red field + suggestion | User |
| V3 | Edit phone field | Invalid format | Block save + warning | User |
| V4 | Confirm order | Contract tag + active contract on tax ID | Notify | Salesperson + Manager |
| V5 | Create invoice | Order already invoiced | Block second invoice | Finance |
| V6 | Vendor bill | Same reference + same amount | Possible-duplicate alert | Finance |
| V7 | Quotation sent | No reply 3 days | Follow-up activity + friendly email | Salesperson + Client |
| V8 | Daily cron | Validity at D-3 | Expiry reminder | Salesperson |
| V9 | Daily cron | Validity at D0 | Expire quotation | — |
| V10 | Order confirmed | — | Create delivery task in Tasks | Technician / Logistics |
| V11 | Delivery validated | — | Generate and send invoice | Client |
| V12 | Daily cron | Invoice overdue D+3 / D+7 / D+15 | Escalating dunning | Client → Salesperson → Manager + GD |
| V13 | Invoice overdue D+15 | Unpaid | Block client credit | Salesperson |
| V14 | Apply discount | Over 10% / above 20% | Request Manager / GD approval | Manager / GD |
| V15 | Daily cron | No purchase in 60 days | Reactivation alert | Salesperson |
| V16 | Cron day 1 | — | Monthly sales report | Management + GD |

V1 to V16 are configured under Settings → Technical → Automation Rules and Scheduled Actions. Configuration belongs in XML data files.

12. Open questions — do not guess

These are unanswered. Leave a clearly marked placeholder in the code and list it in your commit message. Do not invent values. Bring them to me and I will get them confirmed.

- **What a "contract" is.** Shield 4 and the Renewal tag both assume an active-contract object. Is that a subscription, a recurring sale order, or a field on the partner? Nothing gets built here until this is answered.
- **Which module owns the consolidated monthly email**, and what the other four modules expose for it to call.
- **The Export tag colour index**, given Equipment already holds purple.
- **Whether the discount tiers apply to the line discount, the order total, or both**, and what happens when several lines are individually under 10% but the total is over.
- **Who the General Director is in Odoo terms** — a specific user, or a security group.
- **Whether the 60-day inactivity alert counts confirmed orders or paid invoices.**
- **The typo domain list.** Mine is three entries taken from the specification. Ask the client for the real one out of their existing base.

13. Rules for this work

- Never push to `live` or `staging`. Work on a feature branch and open a pull request. The workflow is in `docs/COMMIT_SOP.md`.
- Never modify `l10n_ao`, `zoom_tax_slab`, `bi_birthday_reminder` or `ai_claude`. Another developer owns those and they run the client's live system.
- Everything this module adds is namespaced. External IDs, model names and fields all carry the `sale_gp` or `_gp` marker so our work is always distinguishable from theirs.
- No credentials, API keys, passwords or client data in any commit, ever.
- Configuration belongs in XML data files, not in Python. Only write Python where logic genuinely cannot be expressed as configuration.
- Anything that blocks a save or a confirmation must be overridable by a named group and must say clearly why it fired. A block a user cannot understand becomes a workaround.
- Write the module `README.md` as you go. It covers purpose, what was added, the automations with their triggers, and how to click through and test it by hand.

14. Definition of done

A work item is finished when all of these are true:

- It behaves as this brief describes.
- The module installs cleanly on a fresh database and upgrades cleanly on an existing one.
- No errors or warnings in the server log during install or upgrade.
- The five shields have been tested in staging against real failure cases: emails with no `@`, short and long phone numbers, a repeated tax ID, an order invoiced twice, a vendor bill entered twice.
- The module `README.md` covers it.
- The commit message follows `docs/COMMIT_SOP.md` in full.
- Anything assumed, skipped or left open is written into the "Open" section of the commit message.

15. Suggested order of work

Configuration first, because it is the visible skeleton and the automations depend on it.

- Module scaffold, manifest, folders, README started.
- Tags, colours and the stage-to-state mapping.
- The clean-up script, dry-run mode only, run against a copy of the live base.
- Shields 2 and 3 — email and phone. Self-contained, no dependency on the contract question.
- Shield 1 — duplicate contacts.
- Shield 5 — duplicate invoices.
- Quotation triggers: send, follow-up, D-3 reminder, D0 expiry.
- Order confirmed → delivery task, delivery validated → invoice.
- Discount approval tiers.
- Dunning ladder and credit block.
- Reactivation alert and the monthly report.

Items 1 to 3 are the first working slice and should land first as their own pull request. Shield 4 stays out of every slice until the contract question in section 12 is answered.
