{  # noqa
    "name": "Import BOM Lines",
    "summary": """Import bom lines from CSV file""",
    "category": "Manufacturing/Manufacturing",
    "version": "16.0.0.0.1",
    "sequence": 1,
    "author": "Muhammad Awis",
    "website": "https://bit.ly/3GLgMwG",
    "license": "AGPL-3",
    "depends": ["product", "mrp", "stock"],
    "data": [
        # Security
        "security/ir.model.access.csv",
        # Views
        "views/product_attribute.xml",
        # Wizard
        "wizard/import_bom_lines.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
