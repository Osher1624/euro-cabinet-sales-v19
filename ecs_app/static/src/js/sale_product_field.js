/** @odoo-module **/

import {patch} from "@web/core/utils/patch";
import {SaleOrderLineProductField} from "@sale/js/sale_product_field";
import {OptionalProductsModal} from "@sale_product_configurator/js/product_configurator_modal";

import {
    selectOrCreateProduct,
    getSelectedVariantValues,
    getNoVariantAttributeValues,
} from "sale.VariantMixin";

patch(SaleOrderLineProductField.prototype, "ecs_sale_product_configurator", {
    async _openProductConfigurator(mode) {
        const saleOrderRecord = this.props.record.model.root;
        const pricelistId = saleOrderRecord.data.pricelist_id
            ? saleOrderRecord.data.pricelist_id[0]
            : false;
        const productTemplateId = this.props.record.data.product_template_id[0];
        const $modal = $(
            await this.rpc("/sale_product_configurator/configure", {
                product_template_id: productTemplateId,
                quantity: this.props.record.data.product_uom_qty || 1,
                pricelist_id: pricelistId,
                product_template_attribute_value_ids:
                    this.props.record.data.product_template_attribute_value_ids.records.map(
                        (record) => record.data.id
                    ),
                product_no_variant_attribute_value_ids:
                    this.props.record.data.product_no_variant_attribute_value_ids.records.map(
                        (record) => record.data.id
                    ),
                context: this.context,
            })
        );
        const productSelector = `input[type="hidden"][name="product_id"], input[type="radio"][name="product_id"]:checked`;
        // TODO VFE drop this selectOrCreate and make it so that
        // get_single_product_variant returns first variant as well.
        // and use specified product on edition mode.
        const productId = await selectOrCreateProduct.call(
            this,
            $modal,
            parseInt($modal.find(productSelector).first().val(), 10),
            productTemplateId,
            false
        );
        $modal.find(productSelector).val(productId);
        const variantValues = getSelectedVariantValues($modal);
        const noVariantAttributeValues = getNoVariantAttributeValues($modal);
        /**
         *  `product_custom_attribute_value_ids` records are not loaded in the view bc sub templates
         *  are not loaded in list views. Therefore, we fetch them from the server if the record is
         *  saved. Else we use the value stored on the line.
         */
        const customAttributeValueRecords =
            this.props.record.data.product_custom_attribute_value_ids.records;
        let customAttributeValues = [];
        if (customAttributeValueRecords.length > 0) {
            if (customAttributeValueRecords[0].isNew) {
                customAttributeValues = customAttributeValueRecords.map(
                    (record) => record.data
                );
            } else {
                customAttributeValues = await this.orm.read(
                    "product.attribute.custom.value",
                    this.props.record.data.product_custom_attribute_value_ids
                        .currentIds,
                    ["custom_product_template_attribute_value_id", "custom_value"]
                );
            }
        }
        const formattedCustomAttributeValues = customAttributeValues.map((data) => {
            // NOTE: this dumb formatting is necessary to avoid
            // modifying the shared code between frontend & backend for now.
            return {
                custom_value: data.custom_value,
                custom_product_template_attribute_value_id: {
                    res_id: data.custom_product_template_attribute_value_id[0],
                },
            };
        });
        this.rootProduct = {
            product_id: productId,
            product_template_id: productTemplateId,
            quantity: parseFloat($modal.find('input[name="add_qty"]').val() || 1),
            variant_values: variantValues,
            product_custom_attribute_values: formattedCustomAttributeValues,
            no_variant_attribute_values: noVariantAttributeValues,
        };
        const optionalProductsModal = new OptionalProductsModal(null, {
            rootProduct: this.rootProduct,
            pricelistId: pricelistId,
            okButtonText: this.env._t("Confirm"),
            cancelButtonText: this.env._t("Back"),
            title: this.env._t("Configure"),
            context: this.context,
            mode: mode,
        });
        let modalEl;
        optionalProductsModal.opened(() => {
            modalEl = optionalProductsModal.el;
            this.ui.activateElement(modalEl);
        });
        optionalProductsModal.on("closed", null, async () => {
            // Wait for the event that caused the close to bubble
            await new Promise((resolve) => setTimeout(resolve, 0));
            this.ui.deactivateElement(modalEl);
        });
        optionalProductsModal.open();

        let confirmed = false;
        optionalProductsModal.on("confirm", null, async () => {
            confirmed = true;
            const [mainProduct, ...optionalProducts] =
                await optionalProductsModal.getAndCreateSelectedProducts();

            await this.props.record.update(
                await this._convertConfiguratorDataToUpdateData(mainProduct)
            );
            this._onProductUpdate();
            const optionalProductLinesCreationContext =
                this._convertConfiguratorDataToLinesCreationContext(optionalProducts);
            for (let optionalProductLineCreationContext of optionalProductLinesCreationContext) {
                const line = await saleOrderRecord.data.order_line.addNew({
                    position: "bottom",
                    context: optionalProductLineCreationContext,
                    mode: "readonly", // whatever but not edit !
                    allowWarning: true,
                });
                // FIXME: update sets the field dirty otherwise on the next edit and click out it gets deleted
                line.update({sequence: line.data.sequence});
            }
            saleOrderRecord.data.order_line.unselectRecord();

            // Auto save custom code starts here
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
            // Auto save custom code ends here
        });
        optionalProductsModal.on("closed", null, () => {
            if (confirmed) {
                return;
            }
            if (mode != "edit") {
                this.props.record.update({
                    product_template_id: false,
                    product_id: false,
                    product_uom_qty: 1.0,
                    // TODO reset custom/novariant values (and remove onchange logic?)
                });
            }
        });
    },

    _convertConfiguratorDataToLinesCreationContext: function (optionalProductsData) {
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
