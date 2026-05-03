/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import VariantMixin from "@sale/js/variant_mixin";

/**
 * ECS App - VariantMixin patch
 *
 * Overrides handleCustomValues to:
 * 1. Add numeric validation (positive, max value check) for dimension fields
 * 2. Pre-fill custom values from the sale order's global attribute configuration
 *
 * Also adds getProductAttributeCustomValue RPC helper.
 */
patch(VariantMixin, {
    /**
     * @override
     * Extends the base handleCustomValues to add:
     * - Numeric input validation with error messages
     * - Pre-fill from sale order global attribute config via RPC
     */
    async handleCustomValues($target) {
        const $variantContainer = $target.is("select")
            ? $target.closest("li")
            : $target.closest("ul").closest("li");
        const $customInput = $target.is("select")
            ? $target.find("option:selected")
            : $target.is(":checked")
            ? $target
            : false;

        if (!$variantContainer || !$customInput) {
            return;
        }

        if ($customInput.data("is_custom") !== "True") {
            $variantContainer
                .find(".variant_custom_value, .custom_value_error")
                .remove();
            return;
        }

        const attributeValueId = $customInput.data("value_id");
        const attributeValueName = $customInput.data("value_name");
        const checkValue = parseFloat($customInput.data("check_value")) || 0.0;
        const $existingCustomValue = $variantContainer.find(".variant_custom_value");

        if (
            $existingCustomValue.length &&
            $existingCustomValue.data(
                "custom_product_template_attribute_value_id"
            ) === attributeValueId
        ) {
            return;
        }

        $variantContainer
            .find(".variant_custom_value, .custom_value_error")
            .remove();

        const $input = $("<input>", {
            type: checkValue > 0 ? "number" : "text",
            step: checkValue > 0 ? "0.5" : undefined,
            "data-custom_product_template_attribute_value_id": attributeValueId,
            "data-attribute_value_name": attributeValueName,
            "data-check_value": checkValue,
            class: "variant_custom_value form-control mt-2",
        });

        $input.attr("placeholder", attributeValueName);
        $input.addClass("custom_value_radio");

        const $errorMsg = $("<div>", {
            class: "custom_value_error text-danger small mt-1",
            style: "display: none;",
        });

        $variantContainer.append($input, $errorMsg);

        if ($input.attr("type") === "number") {
            let errorTimeout;

            function showError(message, duration = 2000) {
                clearTimeout(errorTimeout);
                $errorMsg.text(message).show();
                $input.addClass("is-invalid");

                errorTimeout = setTimeout(() => {
                    $errorMsg.fadeOut();
                    $input.removeClass("is-invalid");
                }, duration);
            }

            $input.on("keyup input", function () {
                const value = parseFloat($(this).val());

                if ($(this).val() === "") return;

                if (isNaN(value)) {
                    showError("Please enter a valid number");
                } else if (value <= 0) {
                    $(this).val("");
                    showError(
                        value === 0
                            ? `${attributeValueName} cannot be zero`
                            : `${attributeValueName} cannot be negative`
                    );
                } else if (checkValue > 0.0 && value > checkValue) {
                    $(this).val("");
                    showError(
                        `${attributeValueName} cannot exceed ${checkValue}''`,
                        2500
                    );
                }
            });
        } else {
            $input.val(await this.getProductAttributeCustomValue(attributeValueId));
        }

        const previousCustomValue = $customInput.attr("previous_custom_value");
        if (previousCustomValue) {
            let prevValue = previousCustomValue;
            if ($input.attr("type") === "number") {
                prevValue = Math.max(0, parseFloat(previousCustomValue));
            }
            $input.val(prevValue);
        }
    },

    /**
     * Fetch the pre-configured custom value for a product attribute
     * from the sale order's global attribute configuration.
     *
     * @param {number} attributeValueId - product.template.attribute.value id
     * @returns {Promise<string|number|null>}
     */
    async getProductAttributeCustomValue(attributeValueId) {
        return await rpc("/web/dataset/call_kw", {
            model: "sale.order",
            method: "get_product_attribute_custom_value",
            args: [],
            kwargs: {
                base_url: window.location.href,
                attr_val_id: attributeValueId,
            },
        });
    },
});

