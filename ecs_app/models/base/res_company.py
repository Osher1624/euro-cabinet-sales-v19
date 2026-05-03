from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    order_line_brands = fields.Many2many(comodel_name="product.brand")
