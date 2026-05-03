from odoo import _, fields, models
from odoo.http import request


class Website(models.Model):
    _inherit = "website"

    website_sale_checkout_skip_message = fields.Text(
        string="Website Sale Skip Message",
        required=True,
        translate=True,
        default=lambda s: _(
            "Our team will check your quotation and send you payment information soon."
        ),
    )
    checkout_skip_payment = fields.Boolean(compute="_compute_checkout_skip_payment")
    product_page_image_width = fields.Selection(
        selection_add=[
            ("25_pc", "25 %"),
        ],
        default="25_pc",
        ondelete={"25_pc": "set default"},
    )

    def _get_product_page_proportions(self):
        self.ensure_one()

        return {
            "none": (0, 12),
            "25_pc": (4, 8),
            "50_pc": (6, 6),
            "66_pc": (8, 4),
            "100_pc": (12, 12),
        }.get(self.product_page_image_width)

    def _compute_checkout_skip_payment(self):
        for rec in self:
            if request.session.uid:
                rec.checkout_skip_payment = (
                    request.env.user.partner_id.skip_website_checkout_payment
                )
            else:
                rec.checkout_skip_payment = False
