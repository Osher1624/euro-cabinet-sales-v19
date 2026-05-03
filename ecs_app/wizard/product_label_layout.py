# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class ProductLabelLayout(models.TransientModel):
    _inherit = "product.label.layout"

    print_format = fields.Selection(
        selection_add=[
            ("ecs_46", "4 x 6 ECS"),
        ],
        ondelete={"ecs_46": "set default"},
    )

    def _prepare_report_data(self):
        xml_id, data = super()._prepare_report_data()
        if self.print_format == "ecs_46":
            if self._context.get(
                "active_model"
            ) == "stock.picking" and self._context.get("active_id"):
                xml_id = "ecs_app.report_product_template_label_ecs_46"
                picking_id = self.env["stock.picking"].browse(
                    self._context.get("active_id")
                )
                if (
                    picking_id.picking_type_id.code != "outgoing"
                    and picking_id.group_id.sale_id
                ):
                    raise ValidationError(
                        _(
                            "You can only print 4x6 ECS labels for Orders Outgoing Transfers"
                        )
                    )
                printable_lines = self.move_line_ids.filtered(
                    lambda x: not x.printed and x.qty_done > 0
                )
                if not printable_lines:
                    raise ValidationError(_("Noting to print"))
                printable_lines.printed = True
                data["printable_lines"] = printable_lines.ids
            else:
                raise ValidationError(
                    _("You must select a picking to print 4x6 ECS labels")
                )
        return xml_id, data
