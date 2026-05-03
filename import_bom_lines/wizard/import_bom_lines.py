import base64
import csv
from io import StringIO

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_BOM_IMPORT_HEADER = ["BoM ID", "Component", "Quantity", "Apply on Variants"]
_MAX_ROWS_TO_PROCESS = 1000


class ImportBoMLines(models.TransientModel):
    _name = "import.bom.lines"
    _description = "Import BoM Lines"

    name = fields.Char()
    file = fields.Binary(string="Upload File")

    def import_file(self):
        """
        Import Bill of Materials (BoM) lines from a CSV file.

        This function initiates the process of importing BoM lines from an uploaded CSV file.
        It first validates the file format and then processes the CSV content.

        Returns:
            dict or None: If there are skipped rows during processing, returns a dictionary
            containing an action to download a CSV file with the skipped rows. Otherwise,
            returns None.

        Raises:
            ValidationError: If the file format is invalid or if any processing errors occur
            during the import process.
        """
        self._validate_file()
        return self._process_csv()

    def _validate_file(self):
        """
        Validate the uploaded CSV file.

        This method checks if a file has been uploaded and if it has the correct .csv extension.
        It is typically called before processing the file to ensure its validity.

        Raises:
            ValidationError: If no file is uploaded or if the
            file does not have a .csv extension.

        Returns:
            None
        """
        if not self.file:
            raise ValidationError(_("No file uploaded."))
        if not self.name.endswith(".csv"):
            raise ValidationError(_("Invalid file type. Only CSV files are allowed."))

    def _process_csv(self):
        """
        Process the CSV file and import Bill of Materials (BoM) lines.

        This method decodes the uploaded CSV file, reads its contents, validates the header,
        processes each row, and handles any skipped rows. If there are skipped rows, it creates
        a downloadable CSV file containing those rows.

        Returns:
            dict or None: If there are skipped rows, returns a dictionary containing an action
            to download a CSV file with the skipped rows. Otherwise, returns None.

        Raises:
            ValidationError: If the CSV file is invalid, cannot be read, or if any processing
            errors occur during the import process.
        """
        try:
            file_content = base64.b64decode(self.file).decode("utf-8")
            csv_file = StringIO(file_content)
            csv_reader = csv.reader(csv_file)
            self._validate_csv_header(csv_reader)
            skipped_rows = self._process_csv_rows(csv_reader)

            # If there are skipped rows, create and return a downloadable CSV
            if skipped_rows:
                return self._create_skipped_rows_csv(skipped_rows)

        except csv.Error as e:
            raise ValidationError(_("Error reading CSV file: {}").format(str(e))) from e
        except ValueError as e:
            raise ValidationError(
                _("Error processing CSV data: {}").format(str(e))
            ) from e
        except Exception as e:
            raise ValidationError(
                _("Unexpected error during import: {}").format(str(e))
            ) from e

    def _create_skipped_rows_csv(self, skipped_rows):
        """
        Create a CSV file for skipped rows and prepare it for download.

        This function generates a CSV file containing the rows
        that could not be processed during the Bill of Materials
        (BoM) import. It adds another column for error reasons,
        creates a temporary attachment in Odoo, and returns an
        action to download the CSV file.

        Parameters:
        -----------
        skipped_rows : list
            A list of lists, where each inner list represents
            a row that could not be processed during the BoM import.
            Each row includes the original data and the reason for skipping.

        Returns:
        --------
        dict
            An action dictionary that triggers the download of the generated CSV file.
            The dictionary contains the following keys:
            - 'type': The type of action (ir.actions.act_url).
            - 'url': The URL to download the attachment.
            - 'target': The target of the action (self).
            - 'name': The name of the download action.
        """

        # Prepare CSV headers with an additional error column
        headers = _BOM_IMPORT_HEADER + ["Error Reason"]

        # Create a CSV in memory
        csv_buffer = StringIO()
        csv_writer = csv.writer(csv_buffer)

        # Write headers
        csv_writer.writerow(headers)

        # Write skipped rows
        csv_writer.writerows(skipped_rows)

        # Get the CSV content
        csv_content = csv_buffer.getvalue()
        csv_buffer.close()

        # Create a temporary attachment for download
        attachment = (
            self.env["ir.attachment"]
            .sudo()
            .create(
                {
                    "name": "Skipped_BoM_Import_Rows.csv",
                    "datas": base64.b64encode(csv_content.encode()),
                    "res_model": self._name,
                    "res_id": self.id,
                    "type": "binary",
                }
            )
        )

        # Return action to download the CSV
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
            "name": "Download Skipped Rows",
        }

    @staticmethod
    def _validate_csv_header(csv_reader):
        """
        Validate the CSV file header.

        This method checks if the CSV file header matches the predefined
        import header format. It reads the first row of the CSV file and
        compares it against the expected header.

        Args:
            csv_reader (csv.reader): A CSV reader object positioned at the header row.

        Raises:
            ValidationError: If the CSV header does not match the expected format.
            The error message includes the allowed header format.
        """

        header = next(csv_reader)
        if header != _BOM_IMPORT_HEADER:
            raise ValidationError(
                _(
                    "Invalid CSV file format.\nAllowed header: "
                    + ", ".join(_BOM_IMPORT_HEADER)
                )
            )

    def _process_csv_rows(self, csv_reader):  # noqa
        """
        Process and import Bill of Materials (BoM) lines from a CSV file.

        This method iterates through each row in the CSV file, performing
        comprehensive validation and import of BoM lines. It handles:
        - Row limit enforcement
        - BoM ID and quantity validation
        - Component and variant existence checks
        - Caching of BoM and component data for performance
        - Creation or update of BoM lines

        Args:
            csv_reader (csv.reader): A CSV reader object positioned after the header.

        Returns:
            list: A list of skipped rows with error messages,
                representing rows that could not be processed.
        """

        boms = {}  # Cache for BoM attribute values
        boms_lines = {}  # Cache for existing BoM lines
        skipped_rows = []  # Track rows that couldn't be processed
        processed_rows = 0  # Track the number of processed rows

        # Pre-fetch all products to optimize performance
        components = self._get_components()

        for row in csv_reader:
            processed_rows += 1

            # Prevent potential memory issues
            if processed_rows > _MAX_ROWS_TO_PROCESS:
                skipped_rows.append(row + ["Maximum rows limit exceeded"])
                break

            # Validate row length matches header
            if len(row) != len(_BOM_IMPORT_HEADER):
                skipped_rows.append(
                    row
                    + [
                        f"Invalid row length. Expected {len(_BOM_IMPORT_HEADER)} columns."
                    ]
                )
                continue

            # Extract row data
            bom_id, component, quantity, variants = row
            apply_on_variants = variants.split(",") if variants else []

            try:
                bom_id = int(bom_id)
                if bom_id <= 0:
                    skipped_rows.append(row + [f"Invalid BoM ID: {bom_id}"])
                    continue
            except ValueError:
                skipped_rows.append(row + [f"Invalid BoM ID: {bom_id}"])
                continue

            try:
                quantity = float(quantity)
                if quantity <= 0:
                    skipped_rows.append(row + [f"Invalid quantity: {quantity}"])
                    continue
            except ValueError:
                skipped_rows.append(row + [f"Invalid quantity: {quantity}"])
                continue

            # Load BoM data if not already cached
            if bom_id not in boms:
                bom = self._get_bom(bom_id)
                if not bom:
                    skipped_rows.append(row + [f"BoM with ID {bom_id} not found."])
                    continue

                # Cache attribute values and existing lines for this BoM
                boms[bom_id] = self._get_bom_attribute_values(bom)
                boms_lines[bom_id] = self._get_bom_lines(bom)

            # Validate component exists
            component_id = components.get(component, False)
            if not component_id:
                skipped_rows.append(row + [f"Component {component} not found."])
                continue

            # Validate all variants exist
            skip_row = False
            for av in apply_on_variants:
                if av not in boms[bom_id]:
                    skipped_rows.append(
                        row + [f"Attribute Value {av} not found or inactive."]
                    )
                    skip_row = True
                    break
            if skip_row:
                continue

            # Update or create BoM line
            bom_line = boms_lines[bom_id].get(component_id, False)
            if not bom_line:
                bom_line = self._create_bom_line(
                    bom_id, component_id, quantity, apply_on_variants
                )
                boms_lines[bom_id][component_id] = bom_line
            else:
                self._update_bom_line(bom_line, quantity, apply_on_variants)

        return skipped_rows

    def _get_components(self):
        """
        Retrieve all product components from the database.

        This method fetches all product products and creates a dictionary
        mapping their display names to their database IDs.

        Returns:
            dict: A dictionary where keys are product display names
                  and values are their corresponding database IDs.
        """

        return {
            c["display_name"]: c["id"]
            for c in self.env["product.product"]
            .sudo()
            .with_prefetch(None)
            .search_read([], ["id", "display_name"])
        }

    def _get_bom(self, bom_id):
        """
        Retrieve a Bill of Materials (BoM) by its ID.

        Args:
            bom_id (int): The database ID of the BoM to retrieve.

        Returns:
            mrp.bom: The BoM record if found, otherwise None.
        """

        return self.env["mrp.bom"].sudo().search([("id", "=", bom_id)])

    def _get_bom_attribute_values(self, bom):
        """
        Get active attribute values for a BoM's product template.

        This method retrieves all active product template attribute values
        for a given BoM's product template.

        Args:
            bom (mrp.bom): The Bill of Materials record.

        Returns:
            dict: A dictionary mapping attribute value import names to their IDs.
        """

        return {
            av.import_name: av.id
            for av in self.env["product.template.attribute.value"]
            .sudo()
            .search(
                [
                    ("product_tmpl_id", "=", bom.product_tmpl_id.id),
                    ("ptav_active", "=", True),
                ]
            )
        }

    @staticmethod
    def _get_bom_lines(bom):
        """
        Retrieve all lines for a given Bill of Materials.

        Args:
            bom (mrp.bom): The Bill of Materials record.

        Returns:
            dict: A dictionary mapping product IDs to their corresponding BoM lines.
        """

        return {line.product_id.id: line for line in bom.bom_line_ids}

    def _create_bom_line(self, bom_id, component_id, quantity, apply_on_variants):
        """
        Create a new Bill of Materials line.

        Args:
            bom_id (int): The ID of the parent Bill of Materials.
            component_id (int): The ID of the product component.
            quantity (float): The quantity of the component.
            apply_on_variants (list): List of variant names to apply the line to.

        Returns:
            mrp.bom.line: The newly created BoM line record.
        """

        return (
            self.env["mrp.bom.line"]
            .sudo()
            .create(
                {
                    "product_id": component_id,
                    "product_qty": quantity,
                    "bom_product_template_attribute_value_ids": self._map_variant_ids(
                        apply_on_variants,
                        self._get_bom_attribute_values(self._get_bom(bom_id)),
                    ),
                    "bom_id": bom_id,
                }
            )
        )

    def _update_bom_line(self, bom_line, quantity, apply_on_variants):
        """
        Update an existing Bill of Materials line.

        Args:

            bom_line (mrp.bom.line): The BoM line to update.
            quantity (float): The new quantity for the line.
            apply_on_variants (list): Updated list of variant names.

        Returns:
            None
        """

        bom_line.write(
            {
                "product_qty": quantity,
                "bom_product_template_attribute_value_ids": self._map_variant_ids(
                    apply_on_variants,
                    self._get_bom_attribute_values(self._get_bom(bom_line.bom_id.id)),
                    bom_line,
                ),
            }
        )

    @staticmethod
    def _map_variant_ids(variant, attribute_values, line=False):
        """
        Map variant names to their corresponding database IDs.

        This method converts variant names to their database IDs and
        formats them for Odoo ORM operations.

        Args:
            variant (list): List of variant names.
            attribute_values (dict): Mapping of attribute value names to IDs.
            line (mrp.bom.line, optional): Existing BoM line for update scenarios.

        Returns:
            list or False: A list of ORM commands for variant IDs,
                           or False if no variants are present.
        """

        # Convert variant names to IDs using attribute value mapping
        variant = [attribute_values.get(variant_id) for variant_id in variant]
        if line:
            # Append existing variant IDs when updating a line
            variant += line.bom_product_template_attribute_value_ids.ids

        return [(6, 0, variant)] if variant else False

    @api.onchange("name")
    def _onchange_name(self):
        self._check_csv_file()

    def _check_csv_file(self):
        """
        Check if the uploaded file has a CSV extension.

        This method verifies that the file associated with the current record
        has a '.csv' extension. If the file does not have a '.csv' extension,
        it raises a ValidationError.

        Raises:
            ValidationError: If the file does not have a '.csv' extension.

        Returns:
            None
        """
        if self.name and not self.name.lower().endswith(".csv"):
            raise ValidationError(_("Only CSV files are allowed."))
