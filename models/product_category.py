from odoo import api, fields, models
from odoo.exceptions import AccessError


class ProductCategory(models.Model):
    _inherit = "product.category"
    # Keep consistency checks for company-dependent accounting fields.
    _check_company_auto = True

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía anterior",
        required=False,
        default=False,
        readonly=True,
        copy=False,
        index=True,
        ondelete="restrict",
        help="Asignación anterior conservada como referencia. No limita la "
             "visibilidad de la categoría ni asigna la compañía de sus productos.",
    )
    # Preserve existing company values; they no longer determine access.
    parent_id = fields.Many2one(check_company=False)
    domex_vinyasa = fields.Boolean(
        string="Vinyasa",
        default=False,
        copy=False,
        groups="base.group_system",
        help="Restringe esta categoría, sus subcategorías y sus productos al "
             "grupo Vinyasa. La cuenta principal de administrador conserva acceso.",
    )
    domex_vinyasa_restricted = fields.Boolean(
        string="Acceso Vinyasa requerido",
        compute="_compute_domex_vinyasa_restricted",
        recursive=True,
        store=True,
        compute_sudo=True,
        index=True,
        groups="base.group_system",
        help="Se activa si esta categoría o cualquiera de sus categorías padre "
             "está marcada como Vinyasa.",
    )

    @api.depends("domex_vinyasa", "parent_id.domex_vinyasa_restricted")
    def _compute_domex_vinyasa_restricted(self):
        for category in self:
            category.domex_vinyasa_restricted = (
                category.domex_vinyasa or category.parent_id.domex_vinyasa_restricted
            )

    def write(self, vals):
        if "parent_id" in vals and not self.env.su and not self.env.user.has_group("base.group_system"):
            self.check_access("write")
            parent = self.sudo().browse(vals["parent_id"] or [])
            parent_restricted = bool(parent.domex_vinyasa_restricted)
            for category in self.sudo():
                if category.domex_vinyasa_restricted != bool(category.domex_vinyasa or parent_restricted):
                    raise AccessError(self.env._(
                        "Solo un administrador de Ajustes puede cambiar la categoría "
                        "padre si eso modifica la restricción Vinyasa."
                    ))
        return super().write(vals)

    def unlink(self):
        if not self.env.su and not self.env.user.has_group("base.group_system"):
            self.check_access("unlink")
            # Deletion cascades to children and clears product categories.
            # Do not let that silently remove protection from products.
            if self.sudo().search_count([
                ("id", "child_of", self.ids), ("domex_vinyasa_restricted", "=", True),
            ]):
                raise AccessError(self.env._(
                    "Solo un administrador de Ajustes puede eliminar categorías "
                    "Vinyasa o categorías que contengan subcategorías Vinyasa."
                ))
        return super().unlink()

    def copy_data(self, default=None):
        can_classify = self.env.su or self.env.user.has_group("base.group_system")
        if not can_classify:
            self.check_access("read")
            if any(self.sudo().mapped("domex_vinyasa_restricted")):
                raise AccessError(self.env._(
                    "Solo un administrador de Ajustes puede duplicar categorías Vinyasa."
                ))
        values_list = super().copy_data(default)
        if can_classify and "domex_vinyasa" not in (default or {}):
            # Preserve the flag for administrators. copy=False avoids reading
            # the protected field when normal users duplicate shared categories.
            for category, values in zip(self, values_list):
                if values is not None:
                    values["domex_vinyasa"] = category.domex_vinyasa
        return values_list
