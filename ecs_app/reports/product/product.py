from odoo import models

from odoo.addons.product.report.product_label_report import _prepare_data


class ReportProductECSLabel(models.AbstractModel):
    _name = "report.ecs_app.report_simple_label_ecs_46"
    _description = "Product Label ECS Report"

    def _get_report_values(self, docids, data):
        printable_lines = [
            self.env["stock.move.line"].sudo().browse(int(line))
            for line in data.get("printable_lines", [])
        ]
        data = _prepare_data(self.env, data)
        data["printable_lines"] = printable_lines
        return data
