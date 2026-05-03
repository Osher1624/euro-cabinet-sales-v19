# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, models


class OrderCostStructure(models.AbstractModel):
    _name = "report.ecs_app.order_cost_structure"
    _description = "Order Cost Structure Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        order = self.env["sale.order"].browse(
            docids or [self.env.context.get("active_id")]
        )
        (
            raw_material_dict,
            total_components_cost,
            total_operations_cost,
        ) = order.get_mo_lines()
        return {
            "lines": raw_material_dict,
            "total_components_cost": total_components_cost,
            "total_operations_cost": total_operations_cost,
            "currency": order.currency_id,
            "order": order,
            "collapse_show": "collapse show"
            if data.get("print_detail_report", False)
            else "collapse",
        }
