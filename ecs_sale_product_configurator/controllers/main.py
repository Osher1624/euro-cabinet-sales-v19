# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.sale_product_configurator.controllers.main import ProductConfiguratorController
from odoo.addons.sale.controllers.variant import VariantController


class ESCProductConfiguratorController(ProductConfiguratorController):

    def _show_advanced_configurator(self, product_id, variant_values, pricelist, handle_stock, **kw):
        # Overrider this funcation to render the value of sale global attribute's with template
        product = request.env['product.product'].browse(int(product_id))
        combination = request.env['product.template.attribute.value'].browse(variant_values)

        # Custom code 17-09-2024
        sale_attribute_ids = []
        if request.env.context.get('default_sale_order'):
            sale_id = request.env['sale.order'].browse(request.env.context['default_sale_order'])
            if sale_id.sale_attribute_ids:
                sale_attribute_ids = sale_id.sale_attribute_ids.filtered(lambda l: l.product_category_id.id == product.categ_id.id)
            if sale_attribute_ids:
                for ptav in combination:
                    sale_attribute_id = sale_id.sale_attribute_ids.filtered(lambda l: l in sale_attribute_ids and l.product_attribute_id.id == ptav.attribute_id.id)
                    if sale_attribute_id and sale_attribute_id.attribute_value_id:
                        attibute_value = request.env['product.template.attribute.value'].search([('product_attribute_value_id', '=', sale_attribute_id.attribute_value_id.id), ('product_tmpl_id', '=', product.product_tmpl_id.id)], limit=1)
                        if attibute_value:
                            combination = combination - ptav
                            combination += attibute_value
        # Custom code end
        return super()._show_advanced_configurator(product_id=product_id, variant_values=combination.ids, pricelist=pricelist, handle_stock=handle_stock, **kw)
