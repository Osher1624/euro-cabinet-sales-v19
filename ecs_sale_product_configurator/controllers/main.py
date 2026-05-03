# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Upgraded to Odoo 19 - 2025
#
# NOTE: In Odoo 17+, the product configurator was completely rewritten as an
# OWL component. The old _show_advanced_configurator HTTP controller method
# no longer exists. The sale order global attribute pre-filling logic has been
# moved to the JavaScript layer (ecs_sale_product_configurator JS module).
# This controller is kept as a stub for future backend route overrides.

from odoo import http
from odoo.http import request


class ESCProductConfiguratorController(http.Controller):
    pass
