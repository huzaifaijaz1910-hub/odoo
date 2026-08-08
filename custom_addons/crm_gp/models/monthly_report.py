from collections import defaultdict

from dateutil.relativedelta import relativedelta
from markupsafe import Markup, escape

from odoo import _, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    def _gp_report_period(self):
        """The report runs on day 1 (see data/monthly_report.xml) and
        covers the calendar month that just ended."""
        today = fields.Date.context_today(self)
        period_end = today.replace(day=1)
        period_start = period_end - relativedelta(months=1)
        return period_start, period_end

    def _cron_gp_send_monthly_report(self):
        """Brief section 11. The recipient is an ir.config_parameter
        (crm_gp.monthly_report_recipient_user_id), same placeholder
        pattern as the escalation chain's unresolved people, rather than
        blocking on the brief's undefined "management" - see
        data/monthly_report.xml.
        """
        team = self.env.ref("crm_gp.crm_gp_sales_team", raise_if_not_found=False)
        if not team:
            return
        icp = self.env["ir.config_parameter"].sudo()
        recipient_id = icp.get_param("crm_gp.monthly_report_recipient_user_id")
        recipient = self.env["res.users"].browse(int(recipient_id)).exists() if recipient_id else self.env["res.users"]
        if not recipient or not recipient.email:
            return

        period_start, period_end = self._gp_report_period()
        start_dt = fields.Datetime.to_datetime(period_start)
        end_dt = fields.Datetime.to_datetime(period_end)

        Lead = self.with_context(active_test=False)
        created_in_period = Lead.search([
            ("team_id", "=", team.id),
            ("create_date", ">=", start_dt),
            ("create_date", "<", end_dt),
        ])
        closed_in_period = Lead.search([
            ("team_id", "=", team.id),
            ("date_closed", ">=", start_dt),
            ("date_closed", "<", end_dt),
        ])
        # Cohort for "leads by source" / "conversion per stage": leads that
        # entered the pipeline this month. Cohort for "average days per
        # stage" / won-lost: also includes leads created earlier that
        # closed this month, since their stage-duration and outcome belong
        # to this month's activity even if they started before it.
        cohort = created_in_period | closed_in_period
        won = closed_in_period.filtered(lambda l: l.won_status == "won")
        lost = closed_in_period.filtered(lambda l: l.won_status == "lost")

        body = self._gp_render_monthly_report(period_start, period_end, created_in_period, cohort, won, lost)
        self.env["mail.mail"].sudo().create({
            "subject": _("GotaPura CRM: performance summary for %(month)s", month=period_start.strftime("%B %Y")),
            "body_html": body,
            "email_to": recipient.email,
            "auto_delete": True,
        })

    def _gp_report_stages(self):
        return self.env.ref("crm_gp.crm_gp_stage_new") + \
            self.env.ref("crm_gp.crm_gp_stage_qualified") + \
            self.env.ref("crm_gp.crm_gp_stage_technical_survey") + \
            self.env.ref("crm_gp.crm_gp_stage_proposal") + \
            self.env.ref("crm_gp.crm_gp_stage_negotiation") + \
            self.env.ref("crm_gp.crm_gp_stage_won")

    def _gp_render_monthly_report(self, period_start, period_end, funnel_base, cohort, won, lost):
        stages = self._gp_report_stages()

        # 1. Leads by source
        source_counts = defaultdict(int)
        for lead in funnel_base:
            source_counts[lead.source_id.name or _("Unspecified")] += 1

        # 2. Conversion rate per stage: % of this month's new leads that
        # have spent any time in each stage, using the same
        # duration_tracking data crm's own stage-duration tracking is
        # built on (mail.tracking.duration.mixin, via crm.lead's
        # _track_duration_field = 'stage_id').
        total_new = len(funnel_base) or 1
        conversion_rows = []
        for stage in stages:
            reached = sum(
                1 for lead in funnel_base
                if str(stage.id) in (lead.duration_tracking or {})
            )
            conversion_rows.append((stage.name, reached, 100.0 * reached / total_new))

        # 3. Average days spent in each stage, among leads (this month's
        # cohort) that actually passed through it.
        duration_seconds = defaultdict(list)
        for lead in cohort:
            tracking = lead.duration_tracking or {}
            for stage in stages:
                seconds = tracking.get(str(stage.id))
                if seconds is not None:
                    duration_seconds[stage.id].append(seconds)
        avg_days_rows = []
        for stage in stages:
            values = duration_seconds.get(stage.id, [])
            avg_days = (sum(values) / len(values) / 86400.0) if values else 0.0
            avg_days_rows.append((stage.name, avg_days, len(values)))

        # 4. Won/lost with lost reasons
        lost_reason_counts = defaultdict(int)
        for lead in lost:
            lost_reason_counts[lead.lost_reason_id.name or _("Unspecified")] += 1
        won_revenue = sum(won.mapped("expected_revenue"))

        # 5. Performance per salesperson
        salesperson_stats = defaultdict(lambda: {"assigned": 0, "won": 0, "lost": 0, "won_revenue": 0.0})
        for lead in funnel_base:
            if lead.user_id:
                salesperson_stats[lead.user_id]["assigned"] += 1
        for lead in won:
            if lead.user_id:
                salesperson_stats[lead.user_id]["won"] += 1
                salesperson_stats[lead.user_id]["won_revenue"] += lead.expected_revenue
        for lead in lost:
            if lead.user_id:
                salesperson_stats[lead.user_id]["lost"] += 1

        def row(*cells):
            tds = Markup("").join(Markup("<td>%s</td>") % escape(str(c)) for c in cells)
            return Markup("<tr>%s</tr>") % tds

        def table(headers, rows):
            head = Markup("").join(Markup("<th>%s</th>") % escape(h) for h in headers)
            body_rows = Markup("").join(rows)
            return Markup(
                "<table style='border-collapse:collapse;margin-bottom:16px'>"
                "<tr>%s</tr>%s</table>"
            ) % (head, body_rows)

        parts = [
            Markup("<h2>GotaPura CRM - performance summary: %s</h2>") % escape(period_start.strftime("%B %Y")),

            Markup("<h3>Leads by source</h3>"),
            table([_("Source"), _("Leads")], [
                row(name, count) for name, count in sorted(source_counts.items(), key=lambda kv: -kv[1])
            ]) if source_counts else Markup("<p>No leads created this period.</p>"),

            Markup("<h3>Conversion rate per stage (this month's new leads)</h3>"),
            table([_("Stage"), _("Reached"), _("Conversion")], [
                row(name, reached, "%.1f%%" % pct) for name, reached, pct in conversion_rows
            ]),

            Markup("<h3>Average days spent in each stage</h3>"),
            table([_("Stage"), _("Avg. days"), _("Leads counted")], [
                row(name, "%.1f" % days, n) for name, days, n in avg_days_rows
            ]),

            Markup("<h3>Won / Lost</h3>"),
            Markup("<p>Won: %(won)d opportunities, %(revenue).2f expected revenue.<br/>Lost: %(lost)d opportunities.</p>") % {
                "won": len(won), "revenue": won_revenue, "lost": len(lost),
            },
            table([_("Lost reason"), _("Count")], [
                row(name, count) for name, count in sorted(lost_reason_counts.items(), key=lambda kv: -kv[1])
            ]) if lost_reason_counts else Markup(""),

            Markup("<h3>Performance per salesperson</h3>"),
            table([_("Salesperson"), _("Assigned"), _("Won"), _("Lost"), _("Won revenue")], [
                row(user.name, stats["assigned"], stats["won"], stats["lost"], "%.2f" % stats["won_revenue"])
                for user, stats in sorted(salesperson_stats.items(), key=lambda kv: -kv[1]["won_revenue"])
            ]) if salesperson_stats else Markup("<p>No salesperson activity this period.</p>"),
        ]
        return Markup("").join(parts)
