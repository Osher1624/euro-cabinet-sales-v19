# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    #  Information
    'name': "ECS - Sale Product Configurator",
    'version': '19.0.0.1.0',
    'category': 'Customization',
    'summary': "Sale Product Category Configurator",
    'description': """
        TaskID:4172793
        The goal of this module is to configure product attributes in the sales configurator
        as per the globally defined settings.
    """,
    # Author
    'author': 'Odoo PS',
    'website': 'https://bit.ly/3GLgMwG',
    'license': 'LGPL-3',

    # Dependency
    'depends': ['product', 'sale_product_configurator', 'stock_account'],

    'data': [
        'security/ir.model.access.csv',
        'views/product_catrgory_view.xml',
        'views/product_attribute_view.xml',
        'views/sale_order_view.xml',
        'views/variant_template.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'ecs_sale_product_configurator/static/src/scss/product_attribute.scss',
        ]
    },
    # Other
    'installable': True,
}
