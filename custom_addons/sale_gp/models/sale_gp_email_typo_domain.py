from odoo import fields, models


class SaleGpEmailTypoDomain(models.Model):
    """Configuration list for Shield 2 (brief docs/briefs/sale_gp.md §6, V2).

    Kept as data records rather than a Python literal so the client can add
    or correct entries without a code change.
    """

    _name = "sale.gp.email.typo.domain"
    _description = "GotaPura Shield 2 — Known Typo Email Domain"
    _rec_name = "typo_domain"

    typo_domain = fields.Char(required=True, index=True, help="Misspelled domain, e.g. gmial.com.")
    correct_domain = fields.Char(required=True, help="Suggested correction, e.g. gmail.com.")
    active = fields.Boolean(default=True)

    _typo_domain_unique = models.Constraint(
        "unique(typo_domain)",
        "This typo domain is already configured.",
    )
