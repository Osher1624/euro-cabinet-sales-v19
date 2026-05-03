# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class SaleProductCategory(models.Model):
    _name = "sale.product.category"
    _description = "sale product category"
    _order = 'sequence, id'

    sequence = fields.Integer(string="Sequence", default=1)
    display_type = fields.Selection(
        selection=[
            ('line_section', "Section"),
            ('line_note', "Note"),
        ],
        default=False)
    product_category_id = fields.Many2one('product.category')
    name = fields.Char(related="product_category_id.display_name", string="Name", readonly=False)
    category_attribute_ids = fields.Many2many(related="product_category_id.product_attribute_ids")
    product_attribute_id = fields.Many2one('product.attribute')
    sale_id = fields.Many2one('sale.order', string="Sale order")
    attribute_value_ids = fields.Many2many('product.attribute.value', string="Values")
    attribute_value_id = fields.Many2one('product.attribute.value', string="Value")
