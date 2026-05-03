# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2022-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Amaya Aravind EV (<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

from odoo import models, fields, api


class ProductBrand(models.Model):
    _inherit = 'product.template'

    brand_id = fields.Many2one('product.brand', string='Brand')


class BrandProduct(models.Model):
    _name = 'product.brand'
    _description = 'Product Brand'

    name = fields.Char(string="Name")
    brand_image = fields.Binary()
    member_ids = fields.One2many('product.template', 'brand_id')
    product_count = fields.Integer(
        string='Product Count',
        compute='get_count_products',
        store=True,
    )

    @api.depends('member_ids')
    def get_count_products(self):
        for rec in self:
            rec.product_count = len(rec.member_ids)


class PurchaseBrandPivot(models.Model):
    _inherit = 'purchase.report'

    brand_id = fields.Many2one('product.brand', string='Brand', readonly=True)

    def _select(self):
        return (
            super()._select()
            .replace(
                't.categ_id as category_id,',
                't.categ_id as category_id, t.brand_id as brand_id,',
            )
        )

    def _group_by(self):
        return (
            super()._group_by()
            .replace(
                't.categ_id,',
                't.categ_id, t.brand_id,',
            )
        )
