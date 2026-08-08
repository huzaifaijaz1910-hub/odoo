from odoo import fields, models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    crm_gp_escalation_level = fields.Integer(
        default=0,
        help="Highest GotaPura overdue-escalation level (brief section 8) "
             "reached for this activity. Lives on the activity itself, not "
             "the lead, so it naturally resets to 0 whenever a new activity "
             "(chained or stage-entry) replaces this one.",
    )
