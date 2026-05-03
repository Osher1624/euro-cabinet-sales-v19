# BoM Line Import

**Overview**

This module allows you to import BoM (Bill of Materials) lines from a CSV file into your
Odoo database.

**Features**

- Import BoM lines from a CSV file
- Create or update existing BoM lines
- Validate data before import
- Handle errors during import process

**Installation** _To install this module, follow these steps:_

1. Clone this repository into your Odoo addons directory.
2. Install the module by going to Settings > Modules > Install and searching for "BoM
   Line Import".

**Usage** _To use this module, follow these steps:_

_Prepare your CSV file with the following columns:_

- BoM ID
- Component
- Quantity
- Apply on Variants `(optional)`

**User Interface**

- Go to Manufacturing > BoM Line Import and select the CSV file.
- Click Import to start the import process.

**Technical Details**

This module uses the csv library to read the CSV file and the odoo framework to interact
with the database.

Dependencies Odoo `16.0` or later `csv library`
