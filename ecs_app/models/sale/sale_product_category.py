from odoo import api, fields, models


class SaleProductCategory(models.Model):
    _inherit = "sale.product.category"

    is_custom = fields.Boolean(related="attribute_value_id.is_custom")
    custom_value = fields.Char()

    @api.onchange("attribute_value_id")
    def onchange_attribute_value_id(self):
        if not self.attribute_value_id.is_custom:
            self.custom_value = False
