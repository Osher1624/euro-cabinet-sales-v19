import ast
from collections import defaultdict
from urllib.parse import parse_qs

from werkzeug.urls import url_parse

from odoo import _, api, fields, models

NAME_HTML_FORMAT = """
<span title="%s">
<div>%s %s</div>

<div>%s</div>
<div>%s</div>
</span>
"""


class SaleOrder(models.Model):
    _inherit = "sale.order"

    list_all_items = fields.Boolean()
    is_verified = fields.Boolean(default=False)
    section_order_line = fields.One2many(
        comodel_name="sale.order.line",
        inverse_name="order_id",
        string="Section Adjustment",
        domain=[("display_type", "!=", False)],
        required=False,
    )
    section_sorting = fields.Char()
    check_if_processed = fields.Boolean(default=False)
    processed = fields.Char(default="NO")
    done_mrp_production_count = fields.Integer(
        "Count of Done MO",
        compute="_compute_done_mrp_production",
        groups="mrp.group_mrp_user",
        store=1,
        compute_sudo=True,
    )
    cost_structure_report = fields.Text(
        compute="_compute_cost_structure_report",
        compute_sudo=True,
    )
    total_components_cost = fields.Float(
        compute="_compute_cost_structure_report", compute_sudo=True
    )
    total_operations_cost = fields.Float(
        compute="_compute_cost_structure_report", compute_sudo=True
    )
    grand_total = fields.Float(
        compute="_compute_cost_structure_report", compute_sudo=True
    )
    customer_po = fields.Char("Customer PO", tracking=1)
    project_ref_no = fields.Char("Project RefNo", tracking=1)

    @api.model
    def get_product_attribute_custom_value(self, base_url, attr_val_id):
        """
        Retrieve the custom value for a product attribute from a sale order global info.

        This method parses the sale order URL, extracts the order ID, and searches
        for a matching custom value in the order's attribute configuration. It's used
        primarily to pre-fill custom values in the frontend product configurator.

        Args:
            base_url (str): Complete URL containing the sale order ID in fragment
                Format: 'http://localhost:8069/web#id=1092&model=sale.order&view_type=form'
            attr_val_id (int): ID of the product template attribute value to look up

        Returns:
            float|str|None: Custom value if found, based on these conditions:
                - Returns the custom_value if a matching global configuration line exists
                - Returns None if no matching line is found
                - Returns None if sale order ID is invalid or not found
                - Returns None if URL parsing fails
        """
        # Parse the URL to extract fragment (part after #) using werkzeug's url_parse
        parsed = url_parse(base_url)
        # Extract query parameters from fragment using urllib's parse_qs
        params = parse_qs(parsed.fragment)
        # Get sale order ID from params, defaulting to False if not found
        sale_order_id = params.get("id", [False])[0]

        if sale_order_id:
            # Find sale order record with sudo access for elevated permissions
            active_so = self.sudo().browse(int(sale_order_id))
            # Check if order exists and has attribute configurations
            if active_so and active_so.sale_attribute_ids:
                # Find the product template attribute value record
                product_attr_val = (
                    self.env["product.template.attribute.value"]
                    .sudo()
                    .search([("id", "=", attr_val_id)])
                )
                # Filter global configuration lines to find matching attribute value
                global_config_line = active_so.sale_attribute_ids.filtered(
                    lambda l: l.product_attribute_id.id
                    == product_attr_val.attribute_id.id
                    and l.product_category_id.id
                    == product_attr_val.product_tmpl_id.categ_id.id
                    and l.attribute_value_id.id
                    == product_attr_val.product_attribute_value_id.id
                    and l.attribute_value_id.is_custom
                    and l.custom_value
                )
                # Return custom value if found, None otherwise
                if global_config_line:
                    return global_config_line.custom_value
                return None
            return None
        return None

    @api.depends("mrp_production_ids")
    def _compute_cost_structure_report(self):
        for order in self:
            order._compute_mrp_production_ids()
            (
                raw_material_dict,
                total_operations_cost,
                total_components_cost,
            ) = order.get_mo_lines()
            order.total_components_cost = total_components_cost
            order.total_operations_cost = total_operations_cost
            order.grand_total = total_operations_cost + total_components_cost
            order.cost_structure_report = (
                f'<iframe class="h-100 w-100" src="/report/html/ecs_app.order_cost_structure'
                f'/{order.id}">Cost Analysis Report</iframe>'
            )

    @api.depends("mrp_production_ids")
    def _compute_done_mrp_production(self):
        """
        Compute the count of done manufacturing orders (MO) associated with the sale order.

        This method calculates the number of manufacturing orders that are in the 'done' state
        and associates them with the sale order. It updates the 'done_mrp_production_count'
        field with this count.

        Parameters:
        self (SaleOrder): The sale order record for which to compute the done MO count.

        Returns:
        None. The method updates the 'done_mrp_production_count'
        field of the sale order in-place.
        """
        for order in self:
            order.done_mrp_production_count = len(
                order.mrp_production_ids.filtered(lambda mo: mo.state == "done")
            )

    def get_mo_lines(self):
        # 1. Build dict of raw materials
        raw_material_dict = defaultdict(list)

        # 2. Sum of total_cost_operations
        total_operations_cost = 0.0
        total_components_cost = 0.0

        for mo in self.mrp_production_ids.filtered(lambda mo: mo.state == "done"):
            data = self.env[
                "report.mrp_account_enterprise.mrp_cost_structure"
            ]._get_report_values(mo.ids)

            for line in data["lines"]:
                raw_moves = line.get("raw_material_moves", [])
                for move in raw_moves:
                    if move.get("cost") > 0.0:
                        total_components_cost += move.get("cost", 0.0)
                        product_id = move[
                            "product_id"
                        ]  # this is the raw material product
                        raw_material_dict[product_id].append(
                            {"qty": move["qty"], "cost": move["cost"], "mo": mo}
                        )
                total_operations_cost += line.get("total_cost_operations", 0.0)

        # Convert to regular dict (optional)
        raw_material_dict = dict(raw_material_dict)
        return raw_material_dict, total_components_cost, total_operations_cost

    def action_print_detailed_report(self):
        return self.env.ref("ecs_app.action_cost_struct_order_template").report_action(
            self, data={"print_detail_report": False, "report_type": "html"}
        )

    def _action_cancel(self):
        self.mrp_production_ids.filtered(
            lambda mrp: mrp.state in ("draft", "confirmed")
        ).action_cancel()
        return super()._action_cancel()

    def verify_order(self):
        self.with_context(tracking_disable=True).write(
            {"is_verified": True, "require_signature": True}
        )
        return self.action_quotation_send()

    @api.model_create_multi
    def create(self, values):
        order = super(SaleOrder, self).create(values)
        # Prevent recursion by checking context
        if not order.env.context.get("skip_section_lines", False):
            order._set_optional_for()
            order._set_line_number()
            order._add_section_lines()
        return order

    def write(self, values):
        res = super(SaleOrder, self).write(values)
        if "order_line" in values and not self.env.context.get(
            "skip_section_lines", False
        ):
            self._set_optional_for()
            self._set_line_number()
            self._add_section_lines()

        if "section_order_line" in values:
            self._sort_section()

        return res

    def update_order_line_info(self):
        if self.env.context.get("update_order_line_info", False):
            self._set_optional_for()
            self._set_line_number()
            self._add_section_lines()

    def _set_optional_for(self):
        """
        Set the main product for optional lines in the sale order.

        This function iterates through the lines of the sale order and identifies
        the main product line. It then sets the 'optional_for' field for each
        optional line to the ID of the main product line.

        Parameters:
        self (SaleOrder): The sale order record for which to set the optional_for field.

        Returns:
        None. The function updates the 'optional_for' field of the sale order lines in-place.
        """

        # Maintain a variable to keep track of the current main product
        main_product_line = None

        for line in self.order_line:
            # Check if the current line is a main product
            if not line.is_optional_line:
                main_product_line = line
                continue
            line.optional_for = main_product_line.id

    def _set_line_number(self):
        """
        Sets the line number for each order line in the sale order.

        This function iterates over each order line in the sale order and
        assigns a line number based on certain conditions.
        If the line does not have a display type and is not optional
        for another line, the line number is incremented by 1.
        If the line is optional for another line, the line number is incremented by 0.01.

        Parameters:
        self (SaleOrder): The sale order record for which to set the line number.

        Returns:
        None. The function updates the 'line_number' field of the sale order lines in-place.
        """
        self.env.context = dict(self.env.context, skip_section_lines=True)
        last_number = 0
        for line in self.order_line:
            line.sequence = line.id
            if not line.display_type:
                if not line.optional_for:
                    last_number = int(last_number) + 1
                    line.line_number = float(last_number)
                else:
                    line.line_number = last_number + 0.01
                    last_number += 0.01
        self.env.context = dict(self.env.context, skip_section_lines=False)

    def _add_section_lines(self):
        """
        Adds or updates section lines in the sale order.

        This function iterates through the lines of the sale order and adds or updates
        section lines based on certain conditions. A section line is added if the
        section total is greater than 0.00. If a section line already exists, it is updated;
        otherwise, a new section line is created. The function also removes any section
        lines that are no longer needed.

        Parameters:
        self (SaleOrder): The sale order record for which to add or update section lines.

        Returns:
        None. The function updates the sale order lines in-place.
        """
        if not self:
            return

        self.env.context = dict(self.env.context, skip_section_lines=True)
        if self.section_sorting and len(self.section_sorting) > 2:
            for val in ast.literal_eval(self.section_sorting):
                for line_id, line_vals in val.items():
                    order_line = self.order_line.search([("id", "=", line_id)])
                    if order_line:
                        order_line.write(line_vals)
        existing_sections = self.order_line.filtered(
            lambda l: l.display_type == "line_section" and l.is_section_note_added_auto
        )
        sections_to_keep = self.env["sale.order.line"]

        for line in self.order_line.sorted("sequence"):
            if not line.optional_for:
                section_lines = self.order_line.filtered(
                    lambda l: l.optional_for == line
                )
                section_total = (
                    sum(section_lines.mapped("price_subtotal")) + line.price_subtotal
                )

                if section_total > 0.00:
                    section_line = existing_sections.filtered(
                        lambda s: s.section_for == line
                    )
                    if not section_line:
                        section_vals = {
                            "order_id": line.order_id.id,
                            "display_type": "line_section",
                            "is_section_note_added_auto": True,
                            "section_for": line.id,
                            "name": line.name,
                        }
                        section_line = self.env["sale.order.line"].create(section_vals)

                    section_line.write(
                        {
                            "name": f"Section: {line.product_id.name}"
                            f" (Total: {self.currency_id.symbol}{section_total:.2f})",
                            "sequence": line.sequence - 1,
                        }
                    )
                    sections_to_keep |= section_line

        # Remove sections no longer needed
        (existing_sections - sections_to_keep).unlink()
        self.env.context = dict(self.env.context, skip_section_lines=False)

    def _sort_section(self):
        """
        Sorts the sections in the sale order based on the sequence of the products.

        This function iterates through the sections in the sale order, sorts the products
        within each section, and updates the sequence of the sections and products.

        Parameters:
        self (SaleOrder): The sale order record for which to sort the sections.

        Returns:
        None. The function updates the 'sequence' field of the sections and products in-place.
        """
        sequence = 1
        products_by_section = dict(
            sorted(
                {
                    section: self.order_line.filtered(
                        lambda l: l.optional_for == section.section_for
                        or section.section_for == l
                    )
                    if section.section_for
                    else self.env["sale.order.line"]
                    for section in self.section_order_line
                }.items(),
                key=lambda item: item[0].sequence,  # sort by section.sequence
            )
        )

        for section, products in products_by_section.items():
            section.sequence = sequence
            sequence += 1
            for product in sorted(products, key=lambda p: p.sequence):
                product.sequence = sequence
                sequence += 1
        self.section_sorting = str(
            [
                {line.id: {"sequence": line.sequence, "line_number": line.line_number}}
                for line in self.order_line.sorted("sequence")
            ]
        )

    def _prepare_order_line_update_values(
        self, order_line, quantity, linked_line_id=False, **kwargs
    ):
        values = super()._prepare_order_line_update_values(
            order_line, quantity, linked_line_id=linked_line_id, **kwargs
        )
        values["is_optional_line"] = bool(values.get("linked_line_id", False))
        return values

    def send_quotation_mail(self):
        wiz = (
            self.env["mail.compose.message"]
            .with_context(**self.action_quotation_send()["context"])
            .create({})
        )
        wiz._onchange_template_id_wrapper()
        wiz.action_send_mail()

    def _prepare_order_line_values(
        self,
        product_id,
        quantity,
        linked_line_id=False,
        no_variant_attribute_values=None,
        product_custom_attribute_values=None,
        **kwargs,
    ):
        values = super()._prepare_order_line_values(
            product_id,
            quantity,
            linked_line_id=linked_line_id,
            no_variant_attribute_values=no_variant_attribute_values,
            product_custom_attribute_values=product_custom_attribute_values,
            **kwargs,
        )
        values["is_optional_line"] = bool(values.get("linked_line_id", False))
        return values


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    name = fields.Text(
        compute="_compute_name",
        store=True,
        readonly=False,
        required=True,
        precompute=True,
        string="Name ",
    )
    description = fields.Html(compute="_compute_name_config_html")
    configuration = fields.Html(compute="_compute_name_config_html")
    optional_for = fields.Many2one(comodel_name="sale.order.line")
    line_number = fields.Float(string="LN#")
    price_unit = fields.Float(string="Price")
    product_uom_qty = fields.Float(string="QTY")
    is_optional_line = fields.Boolean()
    is_section_note_added_auto = fields.Boolean()
    section_for = fields.Many2one(comodel_name="sale.order.line")
    sequence = fields.Integer(default=0)
    product_domain = fields.Binary(compute="_compute_product_domain")

    @api.depends("order_id.list_all_items")
    def _compute_product_domain(self):
        """
        Compute the product domain for sale order lines based on company and brand restrictions.

        This method calculates the domain used to filter products available for selection
        in sale order lines. It considers company-specific products and, optionally,
        brand-specific products based on the 'list_all_items' flag in the sale order.

        The computed domain is stored in the 'product_domain' field of each sale order line.

        Parameters:
        self (SaleOrderLine): The sale order line record(s) being processed.

        Returns:
        None. The method updates the 'product_domain' field of the sale order line(s) in-place.
        """
        # Create base domain outside the loop since it's constant except for company_id
        base_domain = [
            ("sale_ok", "=", True),
            "|",
            ("company_id", "=", False),
        ]

        for rec in self:
            # Complete the domain with company-specific condition
            domain = base_domain + [("company_id", "=", rec.company_id.id)]

            # Only compute brand-specific domain if not listing all items
            if not rec.order_id.list_all_items:
                rec.product_domain = [
                    ("brand_id", "in", rec.company_id.order_line_brands.ids),
                ] + domain
            else:
                rec.product_domain = domain

    @api.depends(
        "product_id",
        "product_id.product_template_attribute_value_ids",
        "product_no_variant_attribute_value_ids",
        "product_custom_attribute_value_ids",
        "product_id.description_sale",
        "display_type",
    )
    def _compute_name_config_html(self):  # noqa
        """
        Compute HTML-formatted description and configuration for sale order lines.

        This method generates HTML-formatted strings for the 'description' and 'configuration'
        fields of sale order lines. It considers various product attributes, custom values,
        and variant information to create detailed and formatted descriptions.

        The method is triggered when specific fields are modified,
         as specified in the @api.depends decorator.

        Parameters:
        self (SaleOrderLine): The sale order line record(s) being processed.

        Returns:
        None. The method updates the 'description' and 'configuration'
         fields of the sale order line(s) in-place.

        Side effects:
        - Updates the 'description' field with a formatted HTML
         string containing product details.
        - Updates the 'configuration' field with additional HTML
        -formatted configuration details.
        """
        for rec in self:
            rec.description = rec.configuration = False
            if not rec.display_type:
                desc_one = desc_two = desc_three = desc_other = config = ""
                custom_size = False

                if rec.product_id.description_sale:
                    desc_one = rec.product_id.description_sale.split("\n")[0]
                """
                if rec.product_id.product_template_variant_value_ids:
                    desc_two = ", ".join(
                        pav.name
                        for pav in rec.product_id.product_template_variant_value_ids
                    )
                """
                desc_vals, config_vals = [], []
                ptavs = ( rec.product_id.product_template_variant_value_ids or rec.env["product.template.attribute.value"]
                         )
                for ptav in ptavs:
                    display = (
                        getattr(ptav, "order_line_display", None)
                        or (ptav.product_attribute_value_id and ptav.product_attribute_value_id.order_line_display)
                        or "desc"
                    )
                    label = ptav.name  # or f"{ptav.attribute_id.name}: {ptav.name}" if you want full label
                    (config_vals if display == "config" else desc_vals).append(label)

                desc_two = ", ".join(desc_vals) if desc_vals else ""
                config = (config + ", " if config else "") + ", ".join(config_vals) if config_vals else (config or "")


                size = {
                    "Width": rec.product_id.width,
                    "Height": rec.product_id.height,
                    "Depth": rec.product_id.depth,
                }
                custom_values = {}
                custom_values_place = {}
                if any(v for v in size.values()) or any(
                    ca.custom_value for ca in rec.product_custom_attribute_value_ids
                ):
                    for ca in rec.product_custom_attribute_value_ids:
                        cp_att_value_id = ca.custom_product_template_attribute_value_id
                        dimension = cp_att_value_id.name.capitalize()
                        custom_values[cp_att_value_id.id] = ca.custom_value
                        custom_values_place[cp_att_value_id.id] = [
                            cp_att_value_id.product_attribute_value_id.order_line_display,
                            cp_att_value_id.display_name,
                            ca.custom_value,
                        ]

                        if ca.custom_value and dimension in size:
                            custom_size = True
                            size[dimension] = ca.custom_value

                    desc_three = " ".join(
                        "%s: <span class='fw-bold'>%s''</span>" % (k, v)
                        for k, v in size.items()
                    )
                    if custom_size:
                        desc_three = (
                            f"<span class='fw-bold'>Custom"
                            f" Modifications:</span> {desc_three}"
                        )

                for pnv in rec.product_no_variant_attribute_value_ids:
                    if pnv.name.capitalize() not in size and pnv.name.lower() != "none":
                        if custom_values.get(pnv.id, False):
                            pnv_value = f"""<div>{'<span class=''fw-bold''>%s</span>'
                             % pnv.name}: {custom_values.get(pnv.id)}</div>"""
                            custom_values_place.pop(pnv.id)
                        else:
                            pnv_value = f"<div>{pnv.display_name}</div>"

                        if pnv.id in custom_values and not custom_values.get(
                            pnv.id, False
                        ):
                            pnv_value = ""

                        if (
                            pnv.product_attribute_value_id
                            and pnv.product_attribute_value_id.order_line_display
                            == "desc"
                        ):
                            desc_other += pnv_value
                        else:
                            config += pnv_value
                for val in custom_values_place.values():
                    if val[2]:
                        pnv_value = f"""<div>{'<span class=''fw-bold''>%s</span>'
                                              % val[1]}: {val[2]}</div>"""

                        if val[0] == "desc":
                            desc_other += pnv_value
                        else:
                            config += pnv_value

                rec.description = NAME_HTML_FORMAT % (
                    desc_one,
                    desc_one,
                    f"({desc_two})" if desc_two else "",
                    desc_three,
                    desc_other,
                )
                rec.configuration = config

    @api.model_create_multi
    def create(self, values):
        return super(SaleOrderLine, self).create(values)

    def action_open_order(self):
        """
        Open the sale order associated with the current sale order line.

        This method retrieves the sale order associated with the current sale order line
        and opens it in a form view. The view is opened in edit mode.

        Parameters:
        self (SaleOrderLine): The sale order line record for which to open the
         associated sale order.

        Returns:
        dict: A dictionary containing the action to open the sale order in a form view.
        """
        return {
            "name": _(f"Order {self.order_id.name}"),
            "view_mode": "form",
            "res_model": "sale.order",
            "res_id": self.order_id.id,
            "type": "ir.actions.act_window",
            "target": "current",
            "flags": {"form": {"action_buttons": False}},
            "domain": [("id", "=", self.order_id.id)],
            "context": {
                "create": False,
                "delete": False,
                "edit": False,
            },
        }
class ProductTemplateAttributeValue(models.Model):
    _inherit = "product.template.attribute.value"

    order_line_display = fields.Selection(
        selection=[("desc", "Description"), ("config", "Configuration")],
        related="product_attribute_value_id.order_line_display",
        store=True,
        readonly=False,
    )