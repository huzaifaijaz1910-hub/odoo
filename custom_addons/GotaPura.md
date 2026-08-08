CRM Technical Brief — module \`crm\_gp\`

**Module name:** \`crm\_gp\`. All questions on this brief come to me.

This document is the single source of truth for the CRM work. If something is not written here, do not invent it. Ask.

1\. What this module does

GotaPura sell and install water treatment systems to homes and businesses. Enquiries arrive from their website, phone, WhatsApp, referrals and walk ins, and today nothing chases them automatically.

This module turns Odoo CRM into a pipeline that moves an enquiry from first contact to a signed installation, and chases the salesperson at every step so nothing goes quiet. Every stage sends the customer an email, creates dated work for the salesperson, and escalates up the management chain when that work goes overdue.

The system is used by Portuguese speakers. Every customer facing email must exist in Portuguese and English.

2\. Module identity

Create the module at the repository root as \`crm\_gp\`.

Manifest must declare exactly this:

\`\`\`python {     "name": "GotaPura CRM",     "version": "19.0.1.0.0",     "category": "Sales/CRM",     "summary": "Seven stage sales pipeline with stage automations, escalation and fair lead distribution",     "author": "Supply Steer Technologies",     "website": "[https://supplysteer.com",](https://supplysteer.com",)     "license": "Other proprietary",     "depends": \["crm", "mail", "sale*management"\],     "data": \[         "security/ir.model.access.csv",         "data/crm*stages.xml",         "data/crm*tags.xml",         "data/crm*lost*reasons.xml",         "data/mail*templates.xml",         "data/automation*rules.xml",         "data/ir*cron.xml",     \],     "installable": True,     "application": False, } \`\`\`

Folder layout:

\`\`\` crm*gp/ ├── init.py ├── manifest*\_.py ├── README.md ├── data/ ├── models/ ├── security/ └── views/ \`\`\`

3\. The seven stages

Six sequential stages plus one exit. Create them as \`crm.stage\` records in \`data/crm\_stages.xml\`.

| \# | Stage | Sequence | Meaning |
| :---- | :---- | :---- | :---- |
| **1** | **New** | **10** | **Enquiry received from any channel. Not yet qualified.** |
| **2** | **Qualified** | **20** | **Real need, budget, decision maker and timeline confirmed.** |
| **3** | **Technical Survey** | **30** | **Technical data being collected to size the system.** |
| **4** | **Proposal** | **40** | **Priced proposal sent to the customer.** |
| **5** | **Negotiation** | **50** | **Adjustments, discounts and final terms.** |
| **6** | **Won** | **60** | **Awarded. Contract and installation begin.** |

**Lost is deliberately NOT a stage.** Do not create a Lost column. Odoo already has a "Mark as Lost" button that removes the opportunity from the active view and records a reason. Use it.

Won must have \`is\_won \= True\`.

4\. Lost reasons

Create these five as \`crm.lost.reason\` records. Recording a reason is mandatory, no exceptions.

* Price  
* Competition  
* No response  
* Postponed  
* Out of scope

5\. Tags and colours

Create as \`crm.tag\` records. The colour numbers are Odoo's palette index and must match what is written here, because the same colours are reused across every other module on this project.

| Tag | Colour | Odoo index | Used for |
| :---- | :---- | :---- | :---- |
| Urgent | Red | 1 | Immediate action, under 4 hours. Hot lead, breakdown, deadline driven. |
| High Priority | Orange | 2 | Respond the same day. High value or active negotiation. |
| Medium Priority | Yellow | 3 | Respond within 48 hours. Normal flow. |
| Low Priority | Green | 10 | No urgency. Informational or long term. |
| Residential | Blue | 4 | Household filtration and purification. |
| Business | Purple | 6 | Companies, hospitality, industry. |
| On site Survey | Dark blue | 9 | Survey with a site visit. A fee applies. |
| Online Survey | Cyan | 7 | Survey by form or email. Free. |
| Reactivation 90d | Grey | 8 | Lost opportunity to be recontacted after 90 days. |
| Overdue | Red | 1 | Applied automatically by escalation level 1\. |

Verify each index against the live Odoo 19 palette before committing and correct any that do not match the colour named. The colour name wins, the index is my best reading.

An opportunity carries at most one priority tag, plus whichever segmentation tags apply.

6\. Per stage behaviour

This is the core of the module. Every stage does three things when an opportunity enters it: sends the customer an email, creates dated activities for the salesperson, and starts a clock for the maximum time allowed in that stage.

**Stage 1 — New**

**Customer email:** "We have received your enquiry". Confirms receipt, states that a consultant will make contact within 24 business hours, invites them to reply with any detail in advance.

**Activities created:**

| Activity | Due | Description |
| :---- | :---- | :---- |
| **Contact the lead by call or WhatsApp** | **24 hours** | **First introduction call and confirmation of the need.** |
| **Validate contact details** | **24 hours** | **Confirm name, phone, email and location.** |
| **Apply initial tags** | **Immediate** | **Priority plus customer type.** |

**Maximum time in stage:** 3 days. If no meaningful contact has been made, escalate to the sales manager.

**Also on entry:** assign a salesperson by the fair distribution rule in section 8\.

**Stage 2 — Qualified**

**Customer email:** "Next step: technical survey for your solution". Presents the two survey options: online or email survey, free, via a form link; or on site survey with a technician visiting, for a fee. Both the form link and the fee amount are placeholders, see the open questions in section 12\.

Send this one **4 hours after** the stage change, not immediately.

**Activities created:**

| Activity | Due | Description |
| :---- | :---- | :---- |
| **Send survey email** | **4 hours after stage change** | **Automatic. Presents both survey options.** |
| **Schedule the survey** | **2 days** | **Book the visit or confirm the form was completed.** |
| **Record qualification notes** | **Same day** | **Need, budget, decision maker and timeline, written into the chatter.** |

**Maximum time in stage:** 5 days. If there is no reply to the email, a second phone follow up happens on day 3\.

**Stage 3 — Technical Survey**

**Customer email:** "Technical survey confirmed".

**Activities created:**

| Activity | Due | Description |
| :---- | :---- | :---- |
| **Carry out the survey** | **5 business days** | **Site visit, or analysis of the submitted form.** |
| **Issue the technical report** | **48 hours after the survey** | **Internal document carrying the data for the proposal.** |
| **Confirm missing data** | **Immediate, only if applicable** | **Contact the customer if the form came back incomplete.** |

**Maximum time in stage:** 10 days. If no data arrives by the deadline, contact the customer and reschedule once only.

**Stage 4 — Proposal**

**Customer email:** "Your GotaPura proposal — {reference}". States that the proposal covers the solution, equipment, delivery timeline, warranty and payment terms, and that it is valid for 15 days.

**Activities created:**

| Activity | Due | Description |
| :---- | :---- | :---- |
| **Prepare and send the proposal** | **3 business days after the report** | **Quotation generated in Sales and sent from the opportunity.** |
| **Proposal follow up** | **3 days after sending** | **Call to confirm receipt and answer questions.** |
| **Second follow up** | **7 days after sending** | **Reinforcement email summarising the benefits.** |

**Maximum time in stage:** 7 days without a reply. Then either move to Negotiation if there has been contact, or consider marking as Lost.

**Quotation validity:** proposals are valid for 15 days. See section 9\.

**Stage 5 — Negotiation**

**Customer email:** "Following up on your proposal". Acknowledges their feedback, offers to adjust the solution within technical limits, proposes a short meeting or call.

**Activities created:**

| Activity | Due | Description |
| :---- | :---- | :---- |
| **Negotiation meeting or call** | **2 days after entering the stage** | **Discuss adjustments and the conditions for closing.** |
| **Issue revised proposal** | **24 hours after the meeting** | **New quotation version, where anything changed.** |
| **Periodic follow up** | **Every 2 to 3 days** | **Stay in contact until a decision, without pressuring.** |

**Maximum time in stage:** 15 days. Without a decision, involve the sales manager or mark as Lost with reason "Postponed".

**Stage 6 — Won**

**Customer email:** "Welcome to GotaPura — award confirmation". Confirms the award, says the contract and deposit invoice follow, says the technical team will make contact to schedule installation, introduces the dedicated account manager.

**Activities created:**

| Activity | Due | Description |
| :---- | :---- | :---- |
| **Prepare and send the contract** | **24 hours after the award** | **Issue the contract and the deposit invoice.** |
| **Schedule the installation** | **5 days** | **Coordinate the date with the customer and the technical team.** |
| **Welcome call** | **48 hours** | **Introduce the account manager and the next steps.** |

**Maximum time in stage:** handover to execution within 5 business days of signature.

**Lost (via the Mark as Lost button)**

**Customer email:** "Thank you for your time". A short, warm, personalised thank you that leaves the door open. Sent within 24 hours.

**Activities created:**

| Activity | Due | Description |
| :---- | :---- | :---- |
| **Record the lost reason** | **Immediate** | **Mandatory. Selected when marking as lost.** |
| **Send courtesy email** | **24 hours** | **Automatic.** |
| **Reactivation activity** | **90 days** | **Recontact with news, a promotion or a revised proposal.** |

**Also on lost:** apply the "Reactivation 90d" tag automatically.

7\. Email templates

Ten templates in total: seven customer facing (one per stage plus Lost), and three internal escalation notices from section 8\.

Rules for all of them:

* Written in English, with a Portuguese translation loaded through Odoo's standard translation mechanism. Do not create two separate template records per language.  
* The template picks the language from the customer record, so a Portuguese speaking customer receives Portuguese automatically.  
* Every dynamic value uses Odoo 19 placeholder syntax, for example \`{{ object.partner\_id.name }}\`. Never hardcode a name, a reference or an amount.  
* Sign off is "The GotaPura Sales Team" with the strapline "Where your water is our priority" on the first and last templates in the journey.  
* Plain, warm, professional. Short paragraphs. No marketing language.

The full approved wording for each is in the client's own specification. I will paste the exact English text for each template into this document as we go, so write the templates against what is written here, not from your own drafting.

8\. Overdue escalation chain

When an activity passes its due date without being completed, the opportunity climbs a four level chain. The timing depends on the priority tag and is counted from the activity's due date.

| Level | Action | Urgent | High | Medium and Low |
| :---- | :---- | :---- | :---- | :---- |
| 1 | Remind the assigned salesperson, apply the "Overdue" tag | \+4 hours | \+24 hours | \+48 hours |
| 2 | Add a backup salesperson as follower, with their own activity. Original ownership stays | \+8 hours | \+48 hours | \+96 hours |
| 3 | Escalate to the team supervisor with a summary activity | \+24 hours | \+72 hours | \+7 days |
| 4 | Notify general management by internal email | \+48 hours | \+5 days | \+10 days, conditional |

At level 3 the supervisor's activity must carry a summary: stage, expected value, days overdue and last contact, so they can decide whether to reassign.

At level 4 for medium and low priority only, send the notification **only if** the opportunity's expected revenue is above a threshold the company sets. This avoids flooding management with low value noise. Make the threshold a configuration setting rather than a hardcoded number.

Build each level as a separate automation rule with a time based trigger on the activity due date.

9\. Quotation validity

Proposals are valid for 15 days from sending.

* A reminder goes out 3 days before expiry.  
* At day 15 the quotation expires automatically, so out of date prices cannot keep circulating.

Odoo's \`validity\_date\` on the quotation is the field to drive this from.

10\. Fair lead distribution

New leads are shared across the sales team rather than piling onto whoever is quickest.

This is Odoo Enterprise, so use the native **Rule Based Assignment** on the sales team configuration rather than writing custom logic. Configure:

* An assignment domain per salesperson.  
* A maximum capacity per salesperson, starting at 15 to 20 open leads.  
* Salespeople who are away on holiday or sick leave are excluded from the rotation.

Urgent leads are assigned manually by the supervisor, so exclude anything tagged Urgent from automatic assignment.

11\. Monthly performance report

On day 1 of every month, send management a performance summary by email. Build it as a scheduled action.

Contents: leads by source, conversion rate per stage, average days spent in each stage, opportunities won and lost with the lost reasons broken down, and performance per salesperson.

12\. Open questions — do not guess

These are unanswered. Leave a clearly marked placeholder in the code and list it in your commit message. Do not invent values. Bring them to me and I will get them confirmed.

* The technical survey form link for the Qualified stage email.  
* The on site survey fee amount, and whether it varies by region.  
* The expected revenue threshold that triggers level 4 escalation for medium and low priority.  
* Who the backup salesperson is at escalation level 2\. A fixed person, or the least loaded team member.  
* The exact sales team structure: how many salespeople, who the supervisor is, who counts as general management.

13\. Rules for this work

* Never push to \`live\` or \`staging\`. Work on a feature branch and open a pull request. The workflow is in \`docs/COMMIT\_SOP.md\`.  
* Never modify \`l10n*ao\`, \`zoom*tax*slab\`, \`bi*birthday*reminder\` or \`ai*claude\`. Another developer owns those and they run the client's live system.  
* Everything this module adds is namespaced. External IDs, model names and fields all carry the \`crm*gp\` or \`*gp\` marker so our work is always distinguishable from theirs.  
* No credentials, API keys, passwords or client data in any commit, ever.  
* Configuration belongs in XML data files, not in Python. Only write Python where logic genuinely cannot be expressed as configuration.  
* Write the module \`README.md\` as you go. It covers purpose, what was added, the automations with their triggers, and how to click through and test it by hand.

14\. Definition of done

A work item is finished when all of these are true:

* It behaves as this brief describes.  
* The module installs cleanly on a fresh database and upgrades cleanly on an existing one.  
* No errors or warnings in the server log during install or upgrade.  
* The module \`README.md\` covers it.  
* The commit message follows \`docs/COMMIT\_SOP.md\` in full.  
* Anything assumed, skipped or left open is written into the "Open" section of the commit message.

15\. Suggested order of work

Configuration first, because it is the visible skeleton and the automations depend on it.

* Module scaffold, manifest, folders, README started.  
* Stages, tags and lost reasons.  
* Fair lead distribution configuration.  
* Email templates, English first, Portuguese translations after.  
* Stage automations that create activities.  
* Quotation validity reminder and expiry.  
* Lost flow, courtesy email and the 90 day reactivation.  
* The four level escalation chain.  
* Monthly report.

Items 1 to 3 are the first working slice and should land first as their own pull request.

