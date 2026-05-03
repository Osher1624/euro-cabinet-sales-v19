from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class BoM(models.Model):
    _inherit = "mrp.bom"

    bom_template_id = fields.Many2one("mrp.bom.template", string="BoM Template")

    @api.constrains("product_tmpl_id", "product_id", "company_id")
    def _check_bom_uniqueness(self):
        for bom in self:
            domain = [
                ("id", "!=", bom.id),
                ("product_tmpl_id", "=", bom.product_tmpl_id.id),
                ("company_id", "=", bom.company_id.id),
            ]
            if bom.product_id:
                domain.append(("product_id", "=", bom.product_id.id))
            else:
                domain.append(("product_id", "=", False))

            if self.search_count(domain) > 0:
                raise ValidationError(
                    _(
                        "You cannot have more than one BoM for the same product or"
                        " product variant in the same company."
                    )
                )


class BoMLines(models.Model):
    _inherit = "mrp.bom.line"

    note = fields.Char()
    bom_line_category = fields.Selection(
        selection=[
            ("material", "Material"),
            ("finish", "Finish"),
            ("hardware", "Hardware"),
            ("drawer", "Drawer"),
        ],
    )
