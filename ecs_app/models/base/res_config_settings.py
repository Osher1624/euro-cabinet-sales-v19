from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    order_line_brands = fields.Many2many(
        comodel_name="product.brand",
        related="company_id.order_line_brands",
        readonly=False,
    )
    website_sale_checkout_skip_message = fields.Text(
        "Website Sale Checkout Skip Message",
        related="website_id.website_sale_checkout_skip_message",
        readonly=False,
    )
