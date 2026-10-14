from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user


VINYASA_GROUP = "product_category_company.group_vinyasa"


@tagged("post_install", "-at_install")
class TestProductCategoryCompany(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a, cls.company_b = cls.env["res.company"].sudo().create([
            {"name": "Category access A"}, {"name": "Category access B"},
        ])
        cls.companies = cls.company_a | cls.company_b
        cls.with_warehouse_module = "domex_warehouse_ids" in cls.env["res.users"]._fields
        if cls.with_warehouse_module:
            cls.warehouse_a, cls.warehouse_b = cls.env["stock.warehouse"].sudo().create([
                {"name": "Category access A", "code": "VGA", "company_id": cls.company_a.id},
                {"name": "Category access B", "code": "VGB", "company_id": cls.company_b.id},
            ])

        def make_user(login, vinyasa=False, settings=False, companies=None):
            companies = companies or cls.companies
            groups = "base.group_user,base.group_multi_company,product.group_product_manager"
            if vinyasa:
                groups += "," + VINYASA_GROUP
            if settings:
                groups += ",base.group_system"
            vals = {}
            if cls.with_warehouse_module:
                warehouses = cls.warehouse_a | cls.warehouse_b
                vals["domex_warehouse_ids"] = [Command.set(
                    warehouses.filtered(lambda w: w.company_id in companies).ids,
                )]
            return new_test_user(
                cls.env(su=True), login=login, groups=groups,
                company_id=cls.company_a.id, company_ids=[Command.set(companies.ids)], **vals,
            )

        cls.user = make_user("category_shared_user")
        cls.member = make_user("category_vinyasa_user", vinyasa=True)
        cls.member_a = make_user("category_vinyasa_company_a", vinyasa=True, companies=cls.company_a)
        cls.settings = make_user("category_settings_user", settings=True)
        cls.primary_admin = cls.env.ref("base.user_admin").sudo()
        cls.primary_admin.write({
            "company_ids": [Command.link(company.id) for company in cls.companies],
            "group_ids": [Command.unlink(cls.env.ref(VINYASA_GROUP).id)],
        })
        categories = cls.env["product.category"].sudo()
        cls.common_a, cls.common_b, cls.vinyasa = categories.create([
            {"name": "Vinyasa test shared A", "company_id": cls.company_a.id},
            {"name": "Vinyasa test shared B", "company_id": cls.company_b.id},
            {"name": "Vinyasa test restricted", "domex_vinyasa": True},
        ])
        cls.child = categories.create({"name": "Vinyasa test child", "parent_id": cls.vinyasa.id})
        cls.grandchild = categories.create({"name": "Vinyasa test grandchild", "parent_id": cls.child.id})
        cls.categories = cls.common_a | cls.common_b | cls.vinyasa | cls.child | cls.grandchild

        def make_product(name, category=None, company=None):
            vals = {
                "name": "Vinyasa test " + name, "type": "service",
                "categ_id": category.id if category else False,
                "company_id": company.id if company else False,
            }
            if cls.with_warehouse_module:
                warehouse = cls.warehouse_b if company == cls.company_b else cls.warehouse_a
                vals["domex_warehouse_ids"] = [Command.set(warehouse.ids)]
            return cls.env["product.template"].sudo().with_context(
                allowed_company_ids=cls.companies.ids,
            ).create(vals)

        cls.common_product = make_product("common", cls.common_b)
        cls.uncategorized = make_product("uncategorized")
        cls.restricted_product = make_product("restricted", cls.vinyasa)
        cls.child_product = make_product("child", cls.grandchild)
        cls.company_b_product = make_product("company B", cls.vinyasa, cls.company_b)
        cls.products = (
            cls.common_product | cls.uncategorized | cls.restricted_product
            | cls.child_product | cls.company_b_product
        )

    def _model(self, name, user=None, companies=None):
        return self.env[name].with_user(user or self.user).with_context(
            allowed_company_ids=(companies or self.company_a).ids,
        )

    def _assert_categories(self, expected, user=None, companies=None):
        model = self._model("product.category", user, companies)
        domain = [("id", "in", self.categories.ids)]
        self.assertEqual(set(model.search(domain).ids), set(expected.ids))
        self.assertEqual({row["id"] for row in model.search_read(domain, ["name"])}, set(expected.ids))
        self.assertEqual({rid for rid, name in model.name_search(domain=domain)}, set(expected.ids))

    def _assert_products(self, expected, user=None, companies=None):
        for name in ("product.template", "product.product"):
            with self.subTest(model=name):
                records = self.products if name == "product.template" else self.products.product_variant_ids
                visible = expected if name == "product.template" else expected.product_variant_ids
                model = self._model(name, user, companies)
                domain = [("id", "in", records.ids)]
                self.assertEqual(set(model.search(domain).ids), set(visible.ids))
                self.assertEqual({rid for rid, title in model.name_search(domain=domain)}, set(visible.ids))

    def test_shared_categories_ignore_legacy_company_and_current_selection(self):
        for companies in (self.company_a, self.company_b, self.company_a | self.company_b):
            self._assert_categories(self.common_a | self.common_b, companies=companies)
        self.assertEqual(self.common_b.company_id, self.company_b)

    def test_new_categories_are_shared_and_have_no_company_default(self):
        category = self._model("product.category").create({"name": "New shared category"})
        self.assertFalse(category.company_id)
        self.assertFalse(category.sudo().domex_vinyasa)
        self.assertFalse(category.sudo().domex_vinyasa_restricted)
        self._model("product.category", companies=self.company_b).browse(category.id).read(["name"])

    def test_group_adds_vinyasa_to_shared_categories(self):
        self._assert_categories(self.categories, self.member)
        self._assert_categories(self.categories, self.member_a)
        self.assertEqual(self.member_a.company_ids, self.company_a)

    def test_only_principal_admin_is_exempt_without_group(self):
        self.assertFalse(self.primary_admin.has_group(VINYASA_GROUP))
        self._assert_categories(self.categories, self.primary_admin)
        self._assert_categories(self.common_a | self.common_b, self.settings)
        self.settings.sudo().write({"name": self.primary_admin.name})
        self._assert_categories(self.common_a | self.common_b, self.settings)

    def test_group_changes_invalidate_access(self):
        self._assert_categories(self.common_a | self.common_b)
        self.user.sudo().write({"group_ids": [Command.link(self.env.ref(VINYASA_GROUP).id)]})
        self._assert_categories(self.categories)
        self.user.sudo().write({"group_ids": [Command.unlink(self.env.ref(VINYASA_GROUP).id)]})
        self._assert_categories(self.common_a | self.common_b)

    def test_direct_read_write_delete_restricted_categories_are_denied(self):
        category = self._model("product.category").browse(self.grandchild.id)
        with self.assertRaises(AccessError):
            category.read(["name"])
        with self.assertRaises(AccessError), self.cr.savepoint():
            category.write({"name": "Forbidden"})
        with self.assertRaises(AccessError), self.cr.savepoint():
            category.unlink()

    def test_create_cannot_link_hidden_categories_by_id(self):
        with self.assertRaises(AccessError), self.cr.savepoint():
            self._model("product.category").create({
                "name": "Forbidden child", "parent_id": self.vinyasa.id,
            })
        for name in ("product.template", "product.product"):
            vals = {"name": "Forbidden Vinyasa product", "type": "service", "categ_id": self.vinyasa.id}
            # The principal admin configures warehouse fields; the test user
            # has no right to write those protected fields during creation.
            with self.subTest(model=name), self.assertRaises(AccessError), self.cr.savepoint():
                self._model(name).create(vals)

    def test_products_and_variants_require_category_access(self):
        self._assert_products(self.common_product | self.uncategorized)
        expected = self.products - self.company_b_product
        self._assert_products(expected, self.member)
        self._assert_products(expected, self.primary_admin)
        for name in ("product.template", "product.product"):
            record = self.restricted_product if name == "product.template" else self.restricted_product.product_variant_id
            with self.assertRaises(AccessError):
                self._model(name).browse(record.id).read(["name"])

    def test_group_does_not_bypass_product_companies(self):
        self._assert_products(self.products - self.company_b_product, self.member_a)
        self._assert_products(self.products, self.member, self.companies)
        with self.assertRaises(AccessError):
            self._model("product.template", self.member_a).browse(self.company_b_product.id).read(["name"])

    def test_flags_and_parent_changes_update_descendants_and_product_searches(self):
        self.assertFalse(self.child.domex_vinyasa)
        self.assertTrue(self.grandchild.domex_vinyasa_restricted)
        self._assert_products(self.common_product | self.uncategorized)
        self.vinyasa.sudo().write({"domex_vinyasa": False})
        self.assertFalse(self.grandchild.domex_vinyasa_restricted)
        self._assert_categories(self.categories)
        self._assert_products(self.products - self.company_b_product)
        self.common_a.sudo().write({"domex_vinyasa": True})
        self.vinyasa.sudo().write({"parent_id": self.common_a.id})
        self.assertTrue(self.grandchild.domex_vinyasa_restricted)
        self._assert_categories(self.common_b)
        self._assert_products(self.common_product | self.uncategorized)
        self.vinyasa.sudo().write({"parent_id": False})
        self.assertFalse(self.grandchild.domex_vinyasa_restricted)
        self._assert_products(self.products - self.company_b_product)

    def test_common_parent_does_not_reveal_restricted_children(self):
        self.vinyasa.sudo().write({"parent_id": self.common_a.id})
        self._assert_categories(self.common_a | self.common_b)
        children = self._model("product.category").search([("id", "child_of", self.common_a.id)])
        self.assertEqual(children, children.browse(self.common_a.id))

    def test_cross_legacy_company_hierarchy_is_allowed_but_cycles_are_not(self):
        self.common_b.sudo().write({"parent_id": self.common_a.id})
        self._assert_categories(self.common_a | self.common_b)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.common_a.sudo().write({"parent_id": self.common_b.id})

    def test_flags_cannot_be_changed_by_non_settings_users(self):
        for user in (self.user, self.member):
            category = self._model("product.category", user).browse(self.common_a.id)
            for field in ("domex_vinyasa", "domex_vinyasa_restricted"):
                with self.subTest(user=user.id, field=field), self.assertRaises(AccessError), self.cr.savepoint():
                    category.write({field: True})
        model = self._model("product.category")
        result = model.load([".id", "domex_vinyasa"], [[str(self.common_a.id), "True"]])
        self.assertTrue(any(message["type"] == "error" for message in result["messages"]))
        self.assertFalse(self.common_a.sudo().domex_vinyasa)

    def test_category_parent_cannot_be_used_to_change_protection(self):
        child = self._model("product.category", self.member).browse(self.child.id)
        with self.assertRaises(AccessError), self.cr.savepoint():
            child.write({"parent_id": self.common_a.id})
        common = self._model("product.category", self.member).browse(self.common_a.id)
        with self.assertRaises(AccessError), self.cr.savepoint():
            common.write({"parent_id": self.vinyasa.id})
        # Reparenting within the same protection remains allowed.
        child.write({"parent_id": self.vinyasa.id})
        common.write({"parent_id": self.common_b.id})

    def test_category_deletion_cannot_remove_protection_through_cascade(self):
        self.vinyasa.sudo().write({"parent_id": self.common_a.id})
        for user, category in ((self.user, self.common_a), (self.member, self.vinyasa)):
            with self.assertRaises(AccessError), self.cr.savepoint():
                self._model("product.category", user).browse(category.id).unlink()
        self.assertTrue(self.grandchild.exists())
        self.assertEqual(self.child_product.categ_id, self.grandchild)

    def test_restricted_category_copy_requires_settings(self):
        common_copy = self._model("product.category").browse(self.common_a.id).copy()
        self.assertFalse(common_copy.sudo().domex_vinyasa_restricted)
        with self.assertRaises(AccessError), self.cr.savepoint():
            self._model("product.category", self.member).browse(self.vinyasa.id).copy()
        copied = self._model("product.category", self.primary_admin).browse(self.vinyasa.id).copy()
        self.assertTrue(copied.domex_vinyasa)
        self.assertTrue(copied.domex_vinyasa_restricted)

    def test_product_recategorization_cannot_remove_protection(self):
        for name in ("product.template", "product.product"):
            record = self.restricted_product if name == "product.template" else self.restricted_product.product_variant_id
            for category_id in (False, self.common_a.id):
                with self.subTest(model=name, category=category_id), self.assertRaises(AccessError), self.cr.savepoint():
                    self._model(name, self.member).browse(record.id).write({"categ_id": category_id})
            self._model(name, self.member).browse(record.id).write({"categ_id": self.child.id})
        self._model("product.template", self.primary_admin).browse(self.restricted_product.id).write({
            "categ_id": self.common_a.id,
        })
        self._assert_products(self.common_product | self.uncategorized | self.restricted_product)

    def test_defaults_and_group_expansion_follow_category_access(self):
        for name in ("product.template", "product.product"):
            model = self._model(name, companies=self.company_b)
            defaults = model.with_context(default_categ_id=self.common_a.id).default_get(["categ_id"])
            self.assertEqual(defaults["categ_id"], self.common_a.id)
            defaults = model.with_context(default_categ_id=self.grandchild.id).default_get(["categ_id"])
            self.assertFalse(defaults.get("categ_id"))
        products = self._model("product.template").with_context(group_expand=True)
        expanded = products._read_group_categ_id(self._model("product.category").browse(), [])
        self.assertIn(self.common_b.id, expanded.ids)
        self.assertFalse(set((self.vinyasa | self.child | self.grandchild).ids) & set(expanded.ids))
        expanded = products.with_context(default_categ_id=self.child.id)._read_group_categ_id(
            self._model("product.category").browse(), [],
        )
        self.assertFalse(expanded)

    def test_legacy_rule_is_replaced_and_new_rules_are_global(self):
        rule = self.env.ref("product_category_company.product_category_active_company_rule")
        self.assertEqual(rule.domain_force, "user._domex_vinyasa_category_domain()")
        for xmlid in (
            "product_category_active_company_rule", "product_template_vinyasa_rule", "product_product_vinyasa_rule",
        ):
            rule = self.env.ref("product_category_company." + xmlid)
            self.assertTrue(rule.active)
            self.assertFalse(rule.groups)
            self.assertTrue(rule.perm_read and rule.perm_write and rule.perm_create and rule.perm_unlink)

    def test_permissive_group_rule_cannot_reveal_vinyasa(self):
        for name in ("product.category", "product.template", "product.product"):
            self.env["ir.rule"].sudo().create({
                "name": "Vinyasa permissive test rule", "model_id": self.env["ir.model"]._get_id(name),
                "groups": [Command.link(self.env.ref("product.group_product_manager").id)],
                "domain_force": "[(1, '=', 1)]",
            })
        self._assert_categories(self.common_a | self.common_b)
        self._assert_products(self.common_product | self.uncategorized)

    def test_category_views_expose_classification_only_to_settings(self):
        for xmlid, view_type in (
            ("product.product_category_form_view", "form"), ("product.product_category_list_view", "list"),
        ):
            for user, expected in ((self.user, False), (self.primary_admin, True)):
                arch = etree.fromstring(self._model("product.category", user).get_view(
                    view_id=self.env.ref(xmlid).id, view_type=view_type,
                )["arch"])
                self.assertEqual(bool(arch.xpath("//field[@name='domex_vinyasa']")), expected)

    def test_vinyasa_group_still_requires_warehouse_assignments(self):
        if not self.with_warehouse_module:
            self.skipTest("Requires domex_product_warehouse_access")
        self.member.sudo().write({"domex_warehouse_ids": [Command.clear()]})
        self._assert_categories(self.categories, self.member)
        self._assert_products(self.products.browse(), self.member)
        self.member.sudo().write({"domex_warehouse_ids": [Command.set(self.warehouse_a.ids)]})
        self._assert_products(self.products - self.company_b_product, self.member)

    def test_accounting_group_also_requires_vinyasa_group(self):
        if not self.with_warehouse_module:
            self.skipTest("Requires domex_product_warehouse_access")
        self.restricted_product.sudo().write({
            "domex_accounting_product": True, "domex_warehouse_ids": [Command.clear()],
        })
        self.member.sudo().write({"domex_warehouse_ids": [Command.clear()]})
        self._assert_products(self.products.browse(), self.member)
        group = self.env.ref("domex_product_warehouse_access.group_accounting_product")
        self.member.sudo().write({"group_ids": [Command.link(group.id)]})
        self._assert_products(self.restricted_product, self.member)
        self.member.sudo().write({"group_ids": [Command.unlink(self.env.ref(VINYASA_GROUP).id)]})
        self._assert_products(self.products.browse(), self.member)
