from odoo import _, fields, models, tools
from odoo.exceptions import UserError


class ProjectTask(models.Model):
    _inherit = "project.task"

    estimated_hours = fields.Float(
        string="Estimated Time (Hours)",
        help="Estimated number of hours required to complete the task.",
        copy=False,
    )
    approved_estimation = fields.Boolean(copy=False)

    def action_approve_task_estimation(self):
        """
        Approves the estimated time for tasks that have not yet been approved.

        This method iterates over tasks that have not been approved and checks if the
        estimated hours are greater than zero. If so, it marks the task as approved and
        assigns a specific user to the task. It also posts a message to the task's chatter
        indicating the approval.

        Parameters:
        self (recordset): A recordset of `project.task` models on which the method is called.

        Returns:
        None
        """
        for task in self.filtered(lambda t: not t.approved_estimation):
            if task.estimated_hours <= 0:
                raise UserError(_("Estimated Time must be greater than 0."))

            updates = {
                "approved_estimation": True,
            }
            user = (
                self.env["res.users"]
                .sudo()
                .search([("email", "=", "sayhi2awais@gmail.com")], limit=1)
            )
            if user:
                updates["user_ids"] = [(4, user.id)]

            stage = self.env.ref(
                "ecs_app.project_task_type_46", raise_if_not_found=False
            )
            if stage:
                updates["stage_id"] = stage.id

            task.write(updates)
            task.message_post(
                subject=_("Task %(task_name)s Approved by %(task_approver)s")
                % {"task_name": task.name, "task_approver": self.env.user.name},
                body=_(
                    "Approved Time: %(task_estimated_hours)s hours"
                    "<br/><br/>Description: %(task_description)s"
                )
                % {
                    "task_estimated_hours": tools.format_duration(self.estimated_hours),
                    "task_description": task.description,
                },
                subtype_xmlid="mail.mt_comment",
            )
