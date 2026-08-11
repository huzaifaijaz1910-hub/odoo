import re

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain

# Brief docs/briefs/sale_gp.md §6 — Shield 1 (V1), duplicate contact. Warning
# only. res.partner in this Odoo build has no "mobile" field (see root
# CLAUDE.md "Environment gotchas"), so the comparison is phone, email, VAT.
# Written fields that should re-check for a duplicate and re-log the chatter
# note (phone_sanitized is computed from "phone", not itself writable).
DUPLICATE_GP_TRIGGER_FIELDS = {"phone", "email", "vat", "duplicate_justification_gp"}

# Brief docs/briefs/sale_gp.md §6 — Shield 2 (V2), wrong email. Warning only.
EMAIL_WHITESPACE_RE_GP = re.compile(r"\s")
EMAIL_SHAPE_RE_GP = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

# Brief §6 — Shield 3 (V3), wrong phone. Hard block.
# res.partner in this Odoo version only carries "phone" (no separate
# "mobile" field), unlike models such as crm.lead. Keep the tuple so the
# shield picks up "mobile" automatically if a future dependency adds it back.
PHONE_FIELDS_GP = ("phone", "mobile")


class ResPartner(models.Model):
    _inherit = "res.partner"

    duplicate_gp_warning = fields.Char(
        string="Duplicate Warning (GP)",
        compute="_compute_duplicate_gp_warning",
        help="Shield 1 (V1): non-blocking warning naming any contact whose phone, "
        "email or tax ID (VAT) already matches this one.",
    )
    duplicate_justification_gp = fields.Char(
        string="Duplicate Justification (GP)",
        help="Shield 1 (V1): optional note explaining why this contact is not a "
        "duplicate of the match(es) named above. Logged to the chatter on save.",
    )

    email_gp_warning = fields.Char(
        string="Email Warning (GP)",
        compute="_compute_email_gp_warning",
        help="Shield 2 (V2): non-blocking format/typo warning for the Email field.",
    )

    @api.depends("phone_sanitized", "email", "vat")
    def _compute_duplicate_gp_warning(self):
        for partner in self:
            matches = partner._duplicate_gp_matches()
            if matches:
                partner.duplicate_gp_warning = _(
                    "Shield 1 (V1): this phone, email or tax ID already belongs to %(names)s.",
                    names=", ".join(matches.mapped("display_name")),
                )
            else:
                partner.duplicate_gp_warning = False

    def _duplicate_gp_matches(self):
        """Shield 1 (brief §6, V1). Other partners sharing phone, email or VAT.

        Uses the sanitized phone number computed natively by the
        mail.thread.phone mixin (from phone_validation), rather than a raw
        string compare, so formatting differences don't hide a duplicate.
        """
        self.ensure_one()
        leaves = []
        if self.phone_sanitized:
            leaves.append(Domain("phone_sanitized", "=", self.phone_sanitized))
        if self.email:
            leaves.append(Domain("email", "=ilike", self.email.strip()))
        if self.vat:
            leaves.append(Domain("vat", "=ilike", self.vat.strip()))
        if not leaves:
            return self.env["res.partner"]
        domain = Domain.OR(leaves)
        if isinstance(self.id, int):
            domain &= Domain("id", "!=", self.id)
        return self.env["res.partner"].sudo().search(domain)

    @api.onchange("phone", "email", "vat")
    def _onchange_duplicate_gp(self):
        matches = self._duplicate_gp_matches()
        if not matches:
            return
        return {
            "warning": {
                "title": _("Shield 1 (V1) — possible duplicate contact"),
                "message": _(
                    "This phone, email or tax ID already belongs to: %(names)s. "
                    "Reuse that contact, or note why this one is different in the "
                    "Duplicate Justification field — it is logged to the chatter.",
                    names=", ".join(matches.mapped("display_name")),
                ),
            }
        }

    def _log_duplicate_gp(self):
        """Shield 1 (brief §6, V1). Records the match and any justification
        to the chatter — this shield warns, it never blocks the save."""
        self.ensure_one()
        matches = self._duplicate_gp_matches()
        if not matches:
            return
        links = Markup(", ").join(match._get_html_link() for match in matches)
        if self.duplicate_justification_gp:
            justification_line = Markup("%s %s") % (
                _("Justification:"),
                self.duplicate_justification_gp,
            )
        else:
            justification_line = _("No justification was recorded.")
        body = Markup("<p>%s %s</p><p>%s</p>") % (
            _("Shield 1 (V1): this contact's phone, email or tax ID matches"),
            links,
            justification_line,
        )
        self.message_post(body=body)

    def action_open_merge_gp(self):
        """Shield 1 (brief §6, V1). Opens Odoo's native contact-merge wizard
        pre-loaded with this contact and its match(es) — no bespoke dedup
        engine, per the brief."""
        self.ensure_one()
        matches = self._duplicate_gp_matches()
        action = self.env["ir.actions.act_window"]._for_xml_id("base.action_partner_merge")
        action["context"] = {
            "active_model": "res.partner",
            "active_ids": (self + matches).ids,
        }
        return action

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        for partner in partners:
            partner._log_duplicate_gp()
        return partners

    def write(self, vals):
        res = super().write(vals)
        if DUPLICATE_GP_TRIGGER_FIELDS & vals.keys():
            for partner in self:
                partner._log_duplicate_gp()
        return res

    @api.depends("email")
    def _compute_email_gp_warning(self):
        for partner in self:
            issue = partner._email_gp_check(partner.email)
            partner.email_gp_warning = issue[0] if issue else False

    def _email_gp_check(self, email):
        """Shield 2 (brief §6, V2). Returns (message, suggested_email) or False.

        Never blocks — the caller decides how to surface the message.
        """
        if not email:
            return False
        email = email.strip()
        if EMAIL_WHITESPACE_RE_GP.search(email):
            return (
                _("This email address has spaces in it."),
                email.replace(" ", ""),
            )
        if "@" not in email:
            return (_("This email address is missing '@'."), False)
        if not EMAIL_SHAPE_RE_GP.match(email):
            return (_("This email address is missing a valid domain."), False)
        local, domain = email.rsplit("@", 1)
        typo = (
            self.env["sale.gp.email.typo.domain"]
            .sudo()
            .search([("typo_domain", "=ilike", domain)], limit=1)
        )
        if typo:
            return (
                _("Possible typo in the domain."),
                f"{local}@{typo.correct_domain}",
            )
        return False

    @api.onchange("email")
    def _onchange_email_gp(self):
        issue = self._email_gp_check(self.email)
        if not issue:
            return
        message, suggestion = issue
        if suggestion:
            message = _("%(message)s Did you mean %(suggestion)s?", message=message, suggestion=suggestion)
        return {
            "warning": {
                "title": _("Shield 2 (V2) — possible email problem"),
                "message": message,
            }
        }

    @api.constrains("phone", "country_id")
    def _check_phone_gp(self):
        """Shield 3 (brief §6, V3). Hard block on a number that cannot dial.

        Uses phone_validation's phonenumbers-backed formatter, so validation
        is per-country (Angola's +244 9XX XXX XXX mask included) without any
        hand-rolled regex. Overridable by the "Data Quality Shield Override"
        group, since a phone number that cannot dial has no legitimate
        exception otherwise (brief §6).
        """
        for partner in self:
            if partner.env.user.has_group("sale_gp.group_phone_shield_override_gp"):
                continue
            for fname in PHONE_FIELDS_GP:
                if fname not in partner._fields:
                    continue
                number = partner[fname]
                if not number:
                    continue
                try:
                    partner._phone_format(fname=fname, raise_exception=True)
                except UserError as error:
                    raise ValidationError(
                        _(
                            "Shield 3 (V3) blocked this save: the %(field)s number "
                            "\"%(number)s\" is not a valid, dialable number "
                            "(%(reason)s). Fix the number, or ask a user in the "
                            "\"Data Quality Shield Override\" group to save it as-is.",
                            field=partner._fields[fname].string,
                            number=number,
                            reason=str(error),
                        )
                    ) from error
