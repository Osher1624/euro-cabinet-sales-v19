from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MRPBoMTemplate(models.Model):
    _name = "mrp.bom.template"
    _description = "BoM Template"
    _order = "id desc"

    name = fields.Char(copy=False)
    active = fields.Boolean(default=True, copy=False)
    product_tmpl_ids = fields.Many2many(
        "product.template", string="Products", required=True, copy=False
    )
    bom_template_line_ids = fields.One2many(
        "mrp.bom.template.line",
        "bom_template_id",
        string="BoM Template Lines",
        copy=False,
    )
    is_a_template = fields.Boolean()
    bom_template_id = fields.Many2one(
        "mrp.bom.template",
        string="BoM Template",
        help="BoM Template to copy the components from.",
    )
    is_readonly = fields.Boolean()
    bom_ids = fields.Many2many("mrp.bom", string="BoMs", copy=False)
    ref_qty_bom_ids = fields.Many2many(
        "mrp.bom", "ref_qty_bom_rel", string="Reference QTY BoMs"
    )
    default_qty_bom_ids = fields.Many2many(
        "mrp.bom", "default_qty_bom_rel", string="Default QTY BoMs"
    )
    bom_count = fields.Integer(copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["is_readonly"] = False
            if self.env.context.get("default_is_a_template"):
                if not vals.get("bom_template_line_ids"):
                    raise ValidationError(_("At least one component must be selected."))
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("mrp.bom.template")
                    or "New BoM Template"
                )
            else:
                if not vals.get("bom_template_id"):
                    raise ValidationError(_("BoM Template is required."))
                bom_template_id = self.browse(vals["bom_template_id"])
                vals["name"] = "BoM From " + bom_template_id.name
                vals["bom_template_line_ids"] = [
                    (
                        0,
                        0,
                        {
                            "product_id": line.product_id.id,
                            "ref_product_id": line.ref_product_id.id,
                            "qty": line.qty,
                            "bom_template_line_id": line.id,
                        },
                    )
                    for line in bom_template_id.bom_template_line_ids
                ]
        return super().create(vals_list)

    def process_boms(self):
        """
        Process and manage Bill of Materials (BoM) templates by creating or updating BoMs
        for selected product templates.

        This method performs the following operations:
        1. Creates a dictionary of template lines for quick component lookup
        2. For each product template:
            - Updates existing BoMs by modifying component quantities or adding new components
            - Creates new BoMs if none exist for the product
        3. Updates variants for all processed BoMs
        4. Updates the template record with processed BoMs and status

        Technical flow:
        1. Maps template lines to {product_id: quantity} dictionary
        2. For each product template:
            - Searches for existing BoM
            - If BoM exists:
                * Updates quantities of existing components
                * Adds new components if needed
            - If no BoM exists:
                * Creates new BoM with all template components
        3. Updates product variants
        4. Updates template record with processed BoMs

        Returns:
            None

        Side effects:
            - Creates or updates mrp.bom records
            - Updates bom_ids, is_readonly, and bom_count on the template record
            - Updates product variants through update_bom_lines_variants
        """
        self.ensure_one()
        bom_obj = self.env["mrp.bom"]
        bom_line_obj = self.env["mrp.bom.line"]
        processed_boms = self.env["mrp.bom"]
        ref_bom = []
        default_bom = []

        # Dictionary mapping product IDs to their quantities from template lines
        line_dict = {line: line.qty for line in self.bom_template_line_ids}

        for product in self.product_tmpl_ids:
            existing_bom = bom_obj.search(
                [
                    ("product_tmpl_id", "=", product.id),
                ],
                limit=1,
            )

            if existing_bom:
                # Update existing BoM components
                existing_line_dict = {
                    line.product_id.id: line for line in existing_bom.bom_line_ids
                }
                for line, qty in line_dict.items():
                    ref_line = existing_line_dict.get(line.ref_product_id.id)
                    if ref_line:
                        qty = ref_line.product_qty
                        ref_bom.append(existing_bom.id)
                    else:
                        default_bom.append(existing_bom.id)

                    if line.product_id.id in existing_line_dict:
                        # Update quantity of existing component if greater than 0
                        if qty > 0:
                            existing_line_dict[line.product_id.id].product_qty = qty
                    else:
                        # Add new component to existing BoM
                        bom_line_obj.create(
                            {
                                "bom_id": existing_bom.id,
                                "product_id": line.product_id.id,
                                "product_qty": qty if qty > 0 else 1.0,
                            }
                        )
                processed_boms |= existing_bom
            else:
                # Create new BoM with template components
                new_bom = bom_obj.create(
                    {
                        "product_tmpl_id": product.id,
                        "bom_template_id": self.id,
                        "product_qty": 1,
                        "type": "normal",
                        "bom_line_ids": [
                            (
                                0,
                                0,
                                {
                                    "product_id": line.product_id.id,
                                    "product_qty": qty if qty > 0 else 1.0,
                                },
                            )
                            for line, qty in line_dict.items()
                        ],
                    }
                )
                default_bom.append(new_bom.id)
                processed_boms |= new_bom

        # Update variants for processed BoMs
        for line in self.bom_template_line_ids:
            line.product_id.product_tmpl_id.with_context(
                from_bom_template=True
            ).update_bom_lines_variants(
                line.bom_template_line_id.attribute_value_setup_ids
            )

        # Update template record with results
        self.write(
            {
                "bom_ids": [(6, 0, processed_boms.ids)],
                "ref_qty_bom_ids": [(6, 0, ref_bom)],
                "default_qty_bom_ids": [(6, 0, default_bom)],
                "is_readonly": True,
                "bom_count": len(processed_boms),
            }
        )

    def action_view_mrp_bom(self):
        self.ensure_one()
        action = self.env.ref("mrp.mrp_bom_form_action").read()[0]
        action.update(
            {
                "domain": [("id", "in", self.bom_ids.ids)],
                "context": {
                    "create": False,
                    "delete": False,
                    "edit": False,
                },
            }
        )
        return action


class MRPBoMTemplateLine(models.Model):
    _name = "mrp.bom.template.line"
    _description = "BoM Template Line"

    bom_template_id = fields.Many2one(
        "mrp.bom.template", string="BoM Template", required=True, ondelete="cascade"
    )
    product_id = fields.Many2one("product.product", string="Component", required=True)
    ref_product_id = fields.Many2one("product.product", string="Reference Component")
    qty = fields.Float(string="Quantity", default=1.0, required=True)
    attribute_value_setup_ids = fields.One2many(
        comodel_name="attribute.value.setup",
        inverse_name="bom_tmpl_line_id",
        string="Attribute Values Setup",
        required=False,
    )
    bom_template_line_id = fields.Many2one("mrp.bom.template.line")

    @api.constrains("product_id", "bom_template_id", "qty")
    def _check_unique_product_and_qty(self):
        for record in self:
            if record.qty < 0:
                raise ValidationError(_("Quantity must be 0 or greater."))

            if (
                self.search_count(
                    [
                        ("bom_template_id", "=", record.bom_template_id.id),
                        ("product_id", "=", record.product_id.id),
                        ("id", "!=", record.id),
                    ]
                )
                > 0
            ):
                raise ValidationError(
                    _("Each product can only appear once in a BoM Components")
                )
