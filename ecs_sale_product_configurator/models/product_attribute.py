# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    product_category_ids = fields.Many2many('product.category', string="Product Category", compute="_compute_product_category")

    def _compute_product_category(self):
        product_category_ids = self.env['product.category'].search([])
        for attr in self:
            attr.product_category_ids = product_category_ids.filtered(lambda l: attr.id in l.product_attribute_ids.ids).ids
