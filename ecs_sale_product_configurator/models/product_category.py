# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    is_show_global_info = fields.Boolean(string="Show on Global Info")
    product_attribute_ids = fields.Many2many(
        comodel_name='product.attribute',
        relation='product_attribute_product_category_rel',
        string='Product Attributes',
        ondelete='restrict'
    )
