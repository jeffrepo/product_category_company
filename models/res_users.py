from odoo import models
from odoo.fields import Domain


class ResUsers(models.Model):
    _inherit = "res.users"

    def _domex_vinyasa_category_domain(self):
        self.ensure_one()
        administrator = self.env.ref("base.user_admin", raise_if_not_found=False)
        if (administrator and self.id == administrator.id) or self.has_group(
            "product_category_company.group_vinyasa"
        ):
            return Domain.TRUE
        # SQL predicate: hierarchy/flag changes do not cache category IDs.
        return Domain("domex_vinyasa_restricted", "=", False)

    def _domex_vinyasa_product_domain(self):
        category_domain = self._domex_vinyasa_category_domain()
        # Keep uncategorised products; other product/company/warehouse rules
        # still intersect this global rule. any! avoids category ACL subqueries.
        return Domain("categ_id", "=", False) | Domain("categ_id", "any!", category_domain)
