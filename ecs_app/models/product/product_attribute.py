from odoo import api, fields, models


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    order_line_display = fields.Selection(
        selection=[
            ("desc", "Description"),
            ("config", "Configuration"),
        ],
        default="config",
        required=True,
    )
    related_attribute_id = fields.Many2one("product.attribute.value")
    product_attribute_id = fields.Many2one("product.attribute")

    @api.model_create_multi
    def create(self, values):
        pas = super(ProductAttribute, self).create(values)
        for ps in pas:
            ps.value_ids.write({"order_line_display": ps.order_line_display})
        return pas

    def write(self, values):
        res = super(ProductAttribute, self).write(values)
        if "order_line_display" in values:
            self.value_ids.write({"order_line_display": self.order_line_display})
        return res


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    order_line_display = fields.Selection(
        selection=[
            ("desc", "Description"),
            ("config", "Configuration"),
        ],
        default="config",
        required=True,
    )
    related_attribute = fields.Many2one("product.attribute.value")


class AttributeValueSetup(models.Model):
    _name = "attribute.value.setup"
    _description = "Attribute Value Setup"
    _rec_name = "attribute_id"

    attribute_id = fields.Many2one(
        "product.attribute", string="Attribute", required=True
    )
    value_ids = fields.Many2many(
        "product.attribute.value", string="Values", required=True
    )
    product_tmpl_id = fields.Many2one("product.template", string="Product")
    bom_tmpl_line_id = fields.Many2one(
        "mrp.bom.template.line", string="BoM Template LIne"
    )

    @api.onchange("attribute_id")
    def onchange_attribute_id(self):
        self.value_ids = False
