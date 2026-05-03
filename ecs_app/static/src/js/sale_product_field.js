/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { SaleOrderLineProductField } from "@sale/js/sale_product_field";

/**
 * ECS App - SaleOrderLineProductField patch
 *
 * Customizations:
 * 1. After product configurator confirms, trigger the hidden
 *    "Update Order Line Info" button to auto-save order line data.
 * 2. Mark optional lines with default_is_optional_line: true
 *    when creating lines via the configurator.
 */
patch(SaleOrderLineProductField.prototype, {
    /**
     * @override
     * After the base configurator flow completes, trigger the
     * update_order_line_info button to persist custom field data.
     */
    async _openProductConfigurator(mode) {
        const saleOrderRecord = this.props.record.model.root;

        // Call the base v19 configurator flow
        await super._openProductConfigurator(mode);

        // Auto-save custom code: trigger update_order_line_info after confirmation
        if (
            saleOrderRecord.resModel === "sale.order" &&
            saleOrderRecord.__viewType === "form"
        ) {
            setTimeout(function () {
                const $updateInfoButton = $(".update_order_line_info");
                if ($updateInfoButton.length) {
                    $updateInfoButton.click();
                }
            }, 100);
        }
    },

    /**
     * @override
     * Ensure optional product lines created via the configurator
     * are flagged with is_optional_line = true.
     */
    _convertConfiguratorDataToLinesCreationContext(optionalProductsData) {
        return optionalProductsData.map((productData) => {
            return {
                default_product_id: productData.product_id,
                default_product_template_id: productData.product_template_id,
                default_product_uom_qty: productData.quantity,
                default_is_optional_line: true,
                default_product_no_variant_attribute_value_ids:
                    productData.no_variant_attribute_values.map(
                        (noVariantAttributeData) => {
                            return [4, parseInt(noVariantAttributeData.value)];
                        }
                    ),
                default_product_custom_attribute_value_ids:
                    productData.product_custom_attribute_values.map(
                        (customAttributeData) => {
                            return [
                                0,
                                0,
                                {
                                    custom_product_template_attribute_value_id:
                                        customAttributeData.custom_product_template_attribute_value_id,
                                    custom_value: customAttributeData.custom_value,
                                },
                            ];
                        }
                    ),
            };
        });
    },
});

