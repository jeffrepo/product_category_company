from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductCategory(models.Model):
    _inherit = "product.category"
    _check_company_auto = True

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        help="Only users working in this company can access this category.",
    )
    parent_id = fields.Many2one(check_company=True)

    @api.constrains("company_id", "parent_id")
    def _check_category_company(self):
        # Check both directions: changing a parent's company must not leave its
        # existing children attached to a category of another company.
        for category in self.sudo():
            if category.parent_id and category.parent_id.company_id != category.company_id:
                raise ValidationError(
                    _("A category and its parent must belong to the same company.")
                )
            if any(child.company_id != category.company_id for child in category.child_id):
                raise ValidationError(
                    _("A category and its children must belong to the same company.")
                )
