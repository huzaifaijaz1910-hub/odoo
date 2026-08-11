from odoo import api, fields, models

# Brief docs/briefs/sale_gp.md §3 — the six-stage sales cycle.
# Odoo's sale.order has no configurable stage model; the six stages are
# derived from state, delivery_status and invoice_status. "Negotiation" has
# no native equivalent, so it is carried on is_negotiation_gp instead.
STAGE_GP_SELECTION = [
    ("quotation", "Quotation"),
    ("sent", "Sent"),
    ("negotiation", "Negotiation"),
    ("confirmed", "Confirmed"),
    ("delivered", "Delivered"),
    ("invoiced_paid", "Invoiced / Paid"),
]

# stage key -> Odoo kanban colour index (brief §3)
STAGE_GP_COLORS = {
    "quotation": 8,
    "sent": 4,
    "negotiation": 2,
    "confirmed": 7,
    "delivered": 4,
    "invoiced_paid": 10,
}


class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_negotiation_gp = fields.Boolean(
        string="In Negotiation",
        default=False,
        copy=False,
        help="Set when a revised quotation is issued after the order was first sent.",
    )
    stage_gp = fields.Selection(
        STAGE_GP_SELECTION,
        string="Stage (GP)",
        compute="_compute_stage_gp",
        store=True,
        help="Read-only view of the six-stage sales cycle, derived from state, "
        "delivery_status and invoice_status (see docs/briefs/sale_gp.md §3).",
    )
    color_gp = fields.Integer(
        string="Stage Colour (GP)",
        compute="_compute_stage_gp",
        store=True,
    )

    # delivery_status (brief §3, stage 5) is defined by sale_stock, which is
    # not in this module's manifest dependencies (brief §2 lists sale_management,
    # not sale_stock). It is read defensively below so the module installs
    # cleanly either way; until that dependency gap is resolved, orders can
    # reach "confirmed" but never compute as "delivered". Flagged, not guessed
    # — see README "Open questions".
    @api.depends("state", "invoice_status", "invoice_ids.payment_state", "is_negotiation_gp")
    def _compute_stage_gp(self):
        for order in self:
            stage = order._get_stage_gp()
            order.stage_gp = stage
            order.color_gp = STAGE_GP_COLORS[stage]

    def _get_stage_gp(self):
        self.ensure_one()
        if self.state in ("sale", "done"):
            if self.invoice_status == "invoiced" and self.invoice_ids and all(
                inv.payment_state == "paid" for inv in self.invoice_ids
            ):
                return "invoiced_paid"
            if "delivery_status" in self._fields and self.delivery_status == "full":
                return "delivered"
            return "confirmed"
        if self.state == "sent":
            if self.is_negotiation_gp:
                return "negotiation"
            return "sent"
        return "quotation"

    def action_quotation_send(self):
        for order in self:
            if order.state == "sent":
                order.is_negotiation_gp = True
        return super().action_quotation_send()
