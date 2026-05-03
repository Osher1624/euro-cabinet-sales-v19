from odoo import api, fields, models


class ProductTemplateAttributeValue(models.Model):

    _inherit = "product.template.attribute.value"

    import_name = fields.Char(compute="_compute_import_name")

    @api.depends("attribute_id", "name")
    def _compute_import_name(self):
        """
        Compute the import_name field for each product template attribute value.

        This method generates a unique import name for each product template attribute value
        by combining the attribute name, value name, and record ID. It replaces commas and
        spaces with underscores to create a consistent format.

        The computed import_name is stored in the import_name field of the
        product.template.attribute.value model.

        Dependencies:
            - attribute_id: The related product attribute
            - name: The name of the attribute value

        Returns:
            None. The result is stored directly in the import_name field.
        """
        for ptav in self:
            ptav.import_name = "%s_%s_%s" % (
                ptav.attribute_id.name.replace(",", "_").replace(" ", "_"),
                ptav.name.replace(",", "_").replace(" ", "_"),
                ptav.id,
            )
