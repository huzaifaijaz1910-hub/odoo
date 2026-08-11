import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

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

    email_gp_warning = fields.Char(
        string="Email Warning (GP)",
        compute="_compute_email_gp_warning",
        help="Shield 2 (V2): non-blocking format/typo warning for the Email field.",
    )

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
