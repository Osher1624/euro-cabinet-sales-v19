# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    sale_attribute_ids = fields.One2many('sale.product.category', 'sale_id', string="Product Attribute")

    def action_configure_product_attribute(self):
        product_category_ids = self.env['product.category'].search([('is_show_global_info', '=', True)])
        sale_category_value = []
        sequence = 1
        for category in product_category_ids:
            sale_attribute_id = self.sale_attribute_ids.filtered(lambda l: l.product_category_id.id == category.id and l.display_type == 'line_section')
            if not sale_attribute_id:
                sale_category_value.append({
                    'sequence': sequence,
                    'display_type': 'line_section',
                    'product_category_id': category.id,
                    'name': category.display_name,
                    'sale_id': self.id,
                })
            product_attribute_ids = category.product_attribute_ids
            if self.sale_attribute_ids:
                sale_attribute_ids = self.sale_attribute_ids.filtered(lambda l: l.product_category_id.id == category.id and not l.display_type)
                if sale_attribute_ids:
                    sequence = sale_attribute_ids and sale_attribute_ids[0].sequence
                    product_attribute_ids = category.product_attribute_ids - sale_attribute_ids.mapped('product_attribute_id')
            for attriibute in product_attribute_ids: 
                sale_category_value.append({
                    'sequence': sequence,
                    'product_category_id': category.id,
                    'product_attribute_id': attriibute.id,
                    'sale_id': self.id,
                })
            sequence += 1
        self.env['sale.product.category'].create(sale_category_value)
