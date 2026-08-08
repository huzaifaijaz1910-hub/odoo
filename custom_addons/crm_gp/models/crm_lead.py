from datetime import datetime, timedelta

from odoo import _, fields, models

# Brief section 8: hour thresholds per escalation level, counted from the
# moment an activity's due date has fully elapsed. "Medium and Low" share a
# column in the brief's table, so they share one tier here.
ESCALATION_THRESHOLDS_HOURS = {
    1: {"urgent": 4, "high": 24, "medium_low": 48},
    2: {"urgent": 8, "high": 48, "medium_low": 96},
    3: {"urgent": 24, "high": 72, "medium_low": 24 * 7},
    4: {"urgent": 48, "high": 24 * 5, "medium_low": 24 * 10},
}


class CrmLead(models.Model):
    _inherit = "crm.lead"

    def _cron_gp_process_overdue_escalations(self):
        """Brief section 8. Runs hourly (see data/escalation_chain.xml) so
        the hour-level thresholds are meaningful even though mail.activity's
        due date is day-granular - the cron supplies the hour precision the
        activity field itself can't.
        """
        team = self.env.ref("crm_gp.crm_gp_sales_team", raise_if_not_found=False)
        if not team:
            return

        today = fields.Date.context_today(self)
        overdue_activities = self.env["mail.activity"].search([
            ("res_model", "=", "crm.lead"),
            ("date_deadline", "<", today),
        ])
        if not overdue_activities:
            return

        leads = self.browse(overdue_activities.mapped("res_id")).exists().filtered(
            lambda l: l.active and l.team_id.id == team.id and not l.stage_id.is_won
        )
        lead_by_id = {l.id: l for l in leads}
        if not lead_by_id:
            return

        icp = self.env["ir.config_parameter"].sudo()
        tag_urgent = self.env.ref("crm_gp.crm_gp_tag_urgent")
        tag_high = self.env.ref("crm_gp.crm_gp_tag_high_priority")
        tag_overdue = self.env.ref("crm_gp.crm_gp_tag_overdue")
        todo_type = self.env.ref("mail.mail_activity_data_todo")
        template_l2 = self.env.ref("crm_gp.crm_gp_template_escalation_l2")
        template_l3 = self.env.ref("crm_gp.crm_gp_template_escalation_l3")
        template_l4 = self.env.ref("crm_gp.crm_gp_template_escalation_l4")

        backup_user = self._gp_escalation_user(icp, "crm_gp.escalation_l2_backup_user_id")
        supervisor_user = self._gp_escalation_user(icp, "crm_gp.escalation_l3_supervisor_user_id")
        management_user = self._gp_escalation_user(icp, "crm_gp.escalation_l4_management_user_id")
        try:
            revenue_threshold = float(icp.get_param("crm_gp.escalation_l4_revenue_threshold", "0.0") or 0.0)
        except ValueError:
            revenue_threshold = 0.0

        now = datetime.now()
        for activity in overdue_activities:
            lead = lead_by_id.get(activity.res_id)
            if not lead:
                continue

            # An activity's due date "passes" at the end of that day, so
            # hours overdue is counted from midnight after date_deadline.
            overdue_since = datetime.combine(activity.date_deadline + timedelta(days=1), datetime.min.time())
            hours_overdue = (now - overdue_since).total_seconds() / 3600.0
            if hours_overdue < 0:
                continue

            if tag_urgent in lead.tag_ids:
                tier = "urgent"
            elif tag_high in lead.tag_ids:
                tier = "high"
            else:
                tier = "medium_low"

            level = activity.crm_gp_escalation_level
            reached = level
            while reached < 4 and hours_overdue >= ESCALATION_THRESHOLDS_HOURS[reached + 1][tier]:
                reached += 1
                self._gp_escalate_level(
                    lead, activity, reached, tier, hours_overdue,
                    tag_overdue, todo_type,
                    backup_user, supervisor_user, management_user, revenue_threshold,
                    template_l2, template_l3, template_l4,
                )
            if reached != level:
                activity.crm_gp_escalation_level = reached

    def _gp_escalation_user(self, icp, param_key):
        user_id = icp.get_param(param_key)
        user = self.env["res.users"].browse(int(user_id)).exists() if user_id else self.env["res.users"]
        return user or self.env.ref("base.user_admin")

    def _gp_escalate_level(self, lead, activity, level, tier, hours_overdue, tag_overdue, todo_type,
                            backup_user, supervisor_user, management_user, revenue_threshold,
                            template_l2, template_l3, template_l4):
        days_overdue = int(hours_overdue // 24)
        activity_label = activity.summary or activity.activity_type_id.name

        if level == 1:
            lead.write({"tag_ids": [(4, tag_overdue.id)]})
            if lead.user_id:
                lead.message_post(
                    body=_(
                        "Overdue: \"%(activity)s\" is now %(hours)d hours overdue. Please follow up.",
                        activity=activity_label, hours=int(hours_overdue),
                    ),
                    partner_ids=lead.user_id.partner_id.ids,
                )

        elif level == 2:
            lead.message_subscribe(partner_ids=backup_user.partner_id.ids)
            lead.activity_schedule(
                activity_type_id=todo_type.id,
                summary=_("Backup follow up: %(lead)s", lead=lead.name),
                note=_(
                    "\"%(activity)s\" is overdue. You have been added as backup salesperson - "
                    "original ownership stays with %(owner)s.",
                    activity=activity_label, owner=lead.user_id.name or _("Unassigned"),
                ),
                user_id=backup_user.id,
            )
            if backup_user.email:
                template_l2.send_mail(lead.id, email_values={"email_to": backup_user.email})

        elif level == 3:
            last_message = lead.message_ids.sorted("date", reverse=True)[:1]
            last_contact = last_message.date if last_message else lead.create_date
            lead.activity_schedule(
                activity_type_id=todo_type.id,
                summary=_("Supervisor review: %(lead)s", lead=lead.name),
                note=_(
                    "Stage: %(stage)s\nExpected value: %(value).2f\nDays overdue: %(days)d\nLast contact: %(contact)s",
                    stage=lead.stage_id.name, value=lead.expected_revenue,
                    days=days_overdue, contact=last_contact,
                ),
                user_id=supervisor_user.id,
            )
            if supervisor_user.email:
                template_l3.send_mail(lead.id, email_values={"email_to": supervisor_user.email})

        elif level == 4:
            if tier == "medium_low" and lead.expected_revenue < revenue_threshold:
                return
            if management_user.email:
                template_l4.send_mail(lead.id, email_values={"email_to": management_user.email})
