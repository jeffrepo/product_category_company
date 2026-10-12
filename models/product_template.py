from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        return self._filter_category_default(values)

    @api.model
    def _filter_category_default(self, values):
        category_id = values.get("categ_id")
        if category_id and not self.env["product.category"].search(
            [
                ("id", "=", category_id),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        ):
            # A saved default or an action context may still reference a
            # category of the previous company. Odoo 19 allows no category.
            values["categ_id"] = False
        return values

    def _read_group_categ_id(self, categories, domain):
        expanded = super()._read_group_categ_id(categories, domain)
        # The native expansion uses sudo(). Reapply the current user's rules
        # before offering additional, empty category groups in product views.
        return self.env["product.category"].search([("id", "in", expanded.ids)])
