from odoo import api, models
from odoo.exceptions import AccessError


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
            [("id", "=", category_id)],
            limit=1,
        ):
            # Keep shared categories across company switches. Clear only
            # defaults that this user cannot read. Odoo 19 allows no category.
            values["categ_id"] = False
        return values

    def _read_group_categ_id(self, categories, domain):
        expanded = super()._read_group_categ_id(categories, domain)
        # The native expansion uses sudo(). Reapply the current user's rules
        # before offering additional, empty category groups in product views.
        return self.env["product.category"].search([("id", "in", expanded.ids)])

    def write(self, vals):
        if "categ_id" in vals and not self.env.su and not self.env.user.has_group("base.group_system"):
            self.check_access("write")
            category = self.env["product.category"].sudo().browse(vals["categ_id"] or [])
            restricted = bool(category.domex_vinyasa_restricted)
            if any(bool(product.categ_id.domex_vinyasa_restricted) != restricted for product in self.sudo()):
                raise AccessError(self.env._(
                    "Solo un administrador de Ajustes puede cambiar un producto "
                    "entre una categoría compartida y una categoría Vinyasa."
                ))
        return super().write(vals)
