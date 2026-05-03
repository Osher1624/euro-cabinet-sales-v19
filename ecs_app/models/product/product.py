from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    width = fields.Float()
    height = fields.Float()
    depth = fields.Float()
    number_of_doors = fields.Integer()
    number_of_drawers = fields.Integer()
    attribute_value_setup_ids = fields.One2many(
        comodel_name="attribute.value.setup",
        inverse_name="product_tmpl_id",
        string="Attribute Values Setup",
        required=False,
    )

    def update_whd_attribute_sequence(self, attribute_id=None, value_ids=None):
        """
        Update the sequence of Width, Height, and Depth (WHD) attribute values for products.

        This function updates the attribute values for products based on the provided
        attribute ID and value IDs. It filters the attribute lines of each product
        and updates the value_ids field with the corresponding value from the input list.

        Args:
            attribute_id (int, optional): The ID of the attribute to be updated.
            value_ids (list, optional): A list of attribute value IDs to be assigned
                                        in sequence to the filtered attribute lines.

        Returns:
            None: This function doesn't return any value. It updates the attribute
                  values in-place for the matching products and attributes.
        """
        if attribute_id and value_ids:
            for product in self:
                for index, attr in enumerate(
                    product.attribute_line_ids.filtered(
                        lambda a: a.attribute_id.id == attribute_id
                        and a.value_count == 1
                        and a.value_ids.id in value_ids
                    )
                ):
                    attr.value_ids = [value_ids[index % 3]]

    def update_bom_lines_variants(self, bom_line_attribute_value_setup=False):
        """
        Update the attribute value variants for Bill of Materials (BoM) lines.

        This method ensures that the BoM lines are updated with the correct attribute
        value variants based on the provided or existing attribute value setups. It
        maps valid attribute values to the BoM lines and updates their product template
        attribute values accordingly.

        Args:
            bom_line_attribute_value_setup (recordset, optional): A recordset of attribute
                value setups to use for updating the BoM lines. If not provided, the
                method uses the `attribute_value_setup_ids` of the product.

        Workflow:
            1. Collects attribute value IDs from the provided or existing setups.
            2. For each BoM line:
                - Maps valid attribute values for the product template.
                - Updates the BoM line's product template attribute values with the
                  valid attribute values and existing ones.

        Raises:
            None

        Returns:
            None: The method updates the BoM lines in place.
        """
        from_bom_template = self.env.context.get("from_bom_template", False)
        for prod in self:
            attribute_value_setup = (
                bom_line_attribute_value_setup
                if from_bom_template
                else prod.attribute_value_setup_ids
            )
            values_setup = [
                item for setup in attribute_value_setup for item in setup.value_ids.ids
            ]
            if values_setup:
                product_values = {}
                for bom_line in prod.bom_line_ids:
                    if bom_line.bom_id.product_tmpl_id not in product_values:
                        valid_values = {
                            av.product_attribute_value_id.id: av.id
                            for av in bom_line.bom_id.product_tmpl_id.valid_product_template_attribute_line_ids._without_no_variant_attributes().product_template_value_ids._only_active()  # noqa
                        }
                        product_values[bom_line.bom_id.product_tmpl_id] = valid_values
                    valid_values = product_values[bom_line.bom_id.product_tmpl_id]
                    set_values = [
                        valid_values[key] for key in values_setup if key in valid_values
                    ] + bom_line.bom_product_template_attribute_value_ids.ids
                    bom_line.bom_product_template_attribute_value_ids = (
                        [(6, 0, set_values)] if set_values else False
                    )

    @api.onchange("width", "height", "depth")
    @api.constrains("width", "height", "depth")
    def _onchange_size(self):
        """
        Validate and constrain the size dimensions of the product.

        This method is triggered when the width, height, or depth fields are changed.
        It checks if any of these dimensions are negative and raises a ValidationError if so.

        Decorators:
            @api.onchange: Triggers the function when these fields change.
            @api.constrains: Applies constraints on these fields.

        Raises:
            ValidationError: If any of width, height, or depth is negative.

        Returns:
            None
        """
        for rec in self:
            if any(s < 0.0 for s in [rec.width, rec.height, rec.depth]):
                raise ValidationError(_("Width, Height and Depth cannot be negative."))
