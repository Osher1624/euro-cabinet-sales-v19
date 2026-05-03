{  # noqa
    "name": "ECS APP",
    "summary": """ECS Customizations""",
    "category": "Sales/Sales",
    "version": "16.0.0.2.8",
    "sequence": 1,
    "author": "Muhammad Awis, MA",
    "website": "https://bit.ly/3GLgMwG",
    "license": "AGPL-3",
    "depends": [
        "product",
        "product_brand_purchase",
        "project",
        "sale",
        "sale_management",
        "sale_product_configurator",
        "sale_stock",
        "sale_margin",
        "stock",
        "website_sale",
        "ecs_sale_product_configurator",
    ],
    "data": [
        # Data
        "data/data.xml",
        "data/mrp_bom_template_data.xml",
        # Security
        "security/ir.model.access.csv",
        # Views
        # Base Views
        "views/base/template.xml",
        "views/base/partner_view.xml",
        "views/base/res_config_settings.xml",
        # Sales Views
        "views/sale/order.xml",
        "views/sale/order_line.xml",
        "views/sale/order_cost_analysis.xml",
        "views/sale/sale_product_category.xml",
        # Mrp Views
        "views/mrp/bom.xml",
        "views/mrp/bom_template.xml",
        # Product Views
        "views/product/product.xml",
        "views/product/product_attribute.xml",
        # Project Views
        "views/project/project_task.xml",
        # Stock Views
        "views/stock/move.xml",
        # Website Views
        "views/web/website_sale_skip_payment.xml",
        "views/web/website_sale_template.xml",
        # Reports
        "reports/sale/order.xml",
        "reports/product/product_product_templates.xml",
        "reports/sale/order_cost_structure_report.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ecs_app/static/src/js/variant_mixin.js",
            "ecs_app/static/src/js/sale_product_field.js",
            "ecs_app/static/src/css/*.css",
        ],
        "web.assets_frontend": [
            "ecs_app/static/src/xml/dialog.xml",
            "ecs_app/static/src/js/variant_mixin.js",
            "ecs_app/static/src/js/sale_product_field.js",
            "ecs_app/static/src/css/order.css",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
