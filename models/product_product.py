from odoo import api, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        # Explicit defaults on delegated fields do not call the template's
        # default_get(), so variants need the same category access filter.
        return self.env["product.template"]._filter_category_default(values)
