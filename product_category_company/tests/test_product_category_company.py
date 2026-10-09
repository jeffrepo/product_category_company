from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user


@tagged("post_install", "-at_install")
class TestProductCategoryCompany(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a, cls.company_b = cls.env["res.company"].create([
            {"name": "Category test A"},
            {"name": "Category test B"},
        ])
        cls.user = new_test_user(
            cls.env,
            login="category_company_test_user",
            groups="base.group_user,base.group_multi_company,product.group_product_manager",
            company_id=cls.company_a.id,
            company_ids=[Command.set((cls.company_a | cls.company_b).ids)],
        )
        cls.category_a, cls.category_b = cls.env["product.category"].sudo().create([
            {"name": "Category isolation A", "company_id": cls.company_a.id},
            {"name": "Category isolation B", "company_id": cls.company_b.id},
        ])

    def _categories(self, company, other_company):
        return self.env["product.category"].with_user(self.user).with_context(
            allowed_company_ids=[company.id, other_company.id],
        )

    def test_active_company_even_when_both_are_selected(self):
        domain = [("id", "in", (self.category_a | self.category_b).ids)]
        categories = self._categories(self.company_a, self.company_b)
        self.assertEqual(categories.search(domain).ids, self.category_a.ids)
        categories = self._categories(self.company_b, self.company_a)
        self.assertEqual(categories.search(domain).ids, self.category_b.ids)

    def test_name_search_excludes_other_company(self):
        categories = self._categories(self.company_a, self.company_b)
        found_ids = [record_id for record_id, _name in categories.name_search("Category isolation")]
        self.assertIn(self.category_a.id, found_ids)
        self.assertNotIn(self.category_b.id, found_ids)

    def test_direct_read_of_other_company_is_denied(self):
        category = self._categories(self.company_a, self.company_b).browse(self.category_b.id)
        with self.assertRaises(AccessError):
            category.read(["name"])

    def test_new_category_defaults_to_active_company(self):
        categories = self._categories(self.company_b, self.company_a)
        category = categories.create({"name": "New category in B"})
        self.assertEqual(category.company_id, self.company_b)

    def test_create_for_other_company_is_denied(self):
        categories = self._categories(self.company_a, self.company_b)
        with self.assertRaises(AccessError), self.cr.savepoint():
            categories.create({"name": "Forbidden B", "company_id": self.company_b.id})

    def test_write_and_delete_other_company_are_denied(self):
        category = self._categories(self.company_a, self.company_b).browse(self.category_b.id)
        with self.assertRaises(AccessError), self.cr.savepoint():
            category.write({"name": "Forbidden rename"})
        with self.assertRaises(AccessError), self.cr.savepoint():
            category.unlink()

    def test_cross_company_parent_is_rejected_even_in_sudo(self):
        with self.assertRaises(UserError), self.cr.savepoint():
            self.category_a.sudo().write({"parent_id": self.category_b.id})

    def test_parent_company_change_cannot_break_children(self):
        self.env["product.category"].sudo().create({
            "name": "Child in A",
            "parent_id": self.category_a.id,
            "company_id": self.company_a.id,
        })
        with self.assertRaises(UserError), self.cr.savepoint():
            self.category_a.sudo().write({"company_id": self.company_b.id})

    def test_parent_in_same_company_is_allowed(self):
        categories = self._categories(self.company_a, self.company_b)
        category = categories.create({
            "name": "Allowed child",
            "parent_id": self.category_a.id,
        })
        self.assertEqual(category.parent_id.id, self.category_a.id)
