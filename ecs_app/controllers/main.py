from odoo import http
from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale


class CheckoutSkipPaymentWebsite(WebsiteSale):
    @http.route()
    def shop_payment_get_status(self, sale_order_id, **post):
        # When skip payment step, the transaction not exists so only render
        # the waiting message in ajax json call
        if not request.website.checkout_skip_payment:
            return super().shop_payment_get_status(sale_order_id, **post)
        return {
            "recall": True,
            "message": request.website._render("ecs_app.order_state_message"),
        }

    @http.route()
    def shop_payment_confirmation(self, **post):
        """When we skip the payment, we'll just confirm the order and send the proper
        confirmation message"""
        order_id = request.session.get("sale_last_order_id")
        if not request.website.checkout_skip_payment or not order_id:
            return super().shop_payment_confirmation(**post)
        order = request.env["sale.order"].sudo().browse(order_id)
        try:
            order.with_context(update_order_line_info=True).update_order_line_info()
            order.with_context(tracking_disable=True).write(
                {"state": "sent", "require_signature": False}
            )
            order.send_quotation_mail()
        except Exception:
            return request.render("ecs_app.confirmation_order_error")
        request.website.sale_reset()
        edit_order_id = request.session.get("edit_order_id", False)
        request.session["edit_order_id"] = False

        return request.render(
            "website_sale.confirmation",
            {
                "order": order,
                "order_tracking_info": self.order_2_return_dict(order),
                "edit_order_id": edit_order_id,
            },
        )

    @http.route(
        "/edit/quotation/<int:order_id>",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def edit_quotation(self, order_id):
        # Check if an order is already being edited
        if request.session.get("edit_order_id"):
            return request.redirect(f"/my/orders/{order_id}")

        if request.params.get("from_dialog") != "true":
            return request.redirect("/shop")

        sale_order = (
            request.env["sale.order"].sudo().with_context(tracking_disable=True)
        )

        if request.session.get("edit_order_id"):
            edit_order = sale_order.browse(request.session["edit_order_id"])
            if edit_order.exists() and edit_order.state in ("draft", "sent"):
                edit_order.with_context(
                    update_order_line_info=True
                ).update_order_line_info()
                request.session["edit_order_id"] = False

        order = sale_order.browse(order_id)
        if "is_delivery" in order.order_line._fields:
            order.sudo().order_line.filtered(lambda l: l.is_delivery).unlink()
        order.state = "draft"

        if not order.exists():
            return request.redirect("/shop")

        request.website = order.website_id
        # Clear the current cart
        request.website.sale_reset()

        # Update cart quantity
        request.session["sale_order_id"] = order.id
        request.session["website_sale_current_pl"] = order.pricelist_id.id

        # Add order lines to the cart
        for line in order.order_line.filtered(lambda l: not l.display_type):
            no_variant_attribute_values = []
            for ptav in line.product_no_variant_attribute_value_ids:
                no_variant_attribute_values.append(
                    {
                        "value": ptav.product_attribute_value_id.id,
                        "attribute_id": ptav.attribute_id.id,
                    }
                )

            custom_values = []
            for custom_value in line.product_custom_attribute_value_ids:
                value_id = custom_value.custom_product_template_attribute_value_id.id
                custom_values.append(
                    {
                        "custom_product_template_attribute_value_id": value_id,
                        "custom_value": custom_value.custom_value,
                    }
                )

            order._cart_update(
                product_id=line.product_id.id,
                line_id=line.id,
                no_variant_attribute_values=no_variant_attribute_values,
                product_custom_attribute_values=custom_values,
            )

        request.session["website_sale_cart_quantity"] = order.cart_quantity
        request.session["edit_order_id"] = order.id
        # Redirect to the cart page
        return request.redirect("/shop/cart")
