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

    def test_manual_company_assignment_changes_visibility(self):
        categories = self._categories(self.company_a, self.company_b)
        categories.browse(self.category_a.id).write({"company_id": self.company_b.id})
        self.assertFalse(categories.search([("id", "=", self.category_a.id)]))
        categories_b = self._categories(self.company_b, self.company_a)
        self.assertEqual(
            categories_b.search([("id", "=", self.category_a.id)]).ids,
            self.category_a.ids,
        )

    def test_hierarchy_can_be_reassigned_in_one_batch(self):
        categories = self._categories(self.company_a, self.company_b)
        child = categories.create({"name": "Batch child", "parent_id": self.category_a.id})
        hierarchy = categories.browse([self.category_a.id, child.id])
        hierarchy.write({"company_id": self.company_b.id})
        categories_b = self._categories(self.company_b, self.company_a)
        moved = categories_b.search([("id", "in", hierarchy.ids)])
        self.assertEqual(set(moved.ids), set(hierarchy.ids))
        self.assertEqual(moved.mapped("company_id"), self.company_b)

    def test_product_default_keeps_category_of_active_company(self):
        env = self._categories(self.company_a, self.company_b).env
        for model_name in ("product.template", "product.product"):
            with self.subTest(model=model_name):
                defaults = env[model_name].with_context(
                    default_categ_id=self.category_a.id,
                ).default_get(["categ_id"])
                self.assertEqual(defaults["categ_id"], self.category_a.id)

    def test_product_default_clears_category_after_company_switch(self):
        env = self._categories(self.company_b, self.company_a).env
        for model_name in ("product.template", "product.product"):
            with self.subTest(model=model_name):
                defaults = env[model_name].with_context(
                    default_categ_id=self.category_a.id,
                ).default_get(["categ_id"])
                self.assertFalse(defaults.get("categ_id"))

    def test_product_default_can_stay_empty(self):
        env = self._categories(self.company_a, self.company_b).env
        for model_name in ("product.template", "product.product"):
            with self.subTest(model=model_name):
                defaults = env[model_name].with_context(default_categ_id=False).default_get(["categ_id"])
                self.assertFalse(defaults.get("categ_id"))

    def test_group_expansion_respects_active_company(self):
        for company, other_company, visible, hidden in (
            (self.company_a, self.company_b, self.category_a, self.category_b),
            (self.company_b, self.company_a, self.category_b, self.category_a),
        ):
            categories = self._categories(company, other_company)
            products = categories.env["product.template"].with_context(group_expand=True)
            expanded = products._read_group_categ_id(categories.browse(), [])
            self.assertIn(visible.id, expanded.ids)
            self.assertNotIn(hidden.id, expanded.ids)

    def test_group_expansion_rejects_foreign_context_default(self):
        categories = self._categories(self.company_a, self.company_b)
        products = categories.env["product.template"].with_context(default_categ_id=self.category_b.id)
        self.assertFalse(products._read_group_categ_id(categories.browse(), []))

    def test_category_assignment_preserves_existing_products(self):
        product = self.env["product.template"].sudo().create({
            "name": "Product assigned by the client",
            "company_id": self.company_a.id,
            "categ_id": self.category_a.id,
        })
        self.category_a.sudo().write({"company_id": self.company_b.id})
        self.assertEqual(product.company_id, self.company_a)
        self.assertEqual(product.categ_id, self.category_a)
