"""
Tests for engineer_onboarding.create_engineer().

Run locally:
    bench --site <your-site> run-tests --app engineer_onboarding

Each test cleans up after itself so they can run in any order.
"""
import frappe
import unittest

from engineer_onboarding.engineer_onboarding.onboarding_utils import create_engineer


TEST_EMAIL = "pytest.engineer@example.com"
TEST_FIRST_NAME = "Pytest"
TEST_LAST_NAME = "Engineer"
TEST_FULL_NAME = f"{TEST_FIRST_NAME} {TEST_LAST_NAME}"
TEST_ACTIVITY_TYPE = "Engineering"  # must exist on the site


class TestCreateEngineer(unittest.TestCase):
    def setUp(self):
        self._cleanup()
        # create_engineer() requires the User to already exist (button only
        # appears on existing User records in the UI)
        self._create_test_user()

    def tearDown(self):
        self._cleanup()

    def _create_test_user(self, roles=None, role_profile=None):
        user_doc = {
            "doctype": "User",
            "email": TEST_EMAIL,
            "first_name": TEST_FIRST_NAME,
            "last_name": TEST_LAST_NAME,
            "send_welcome_email": 0,
        }
        if role_profile:
            user_doc["role_profile_name"] = role_profile
        if roles:
            user_doc["roles"] = [{"role": r} for r in roles]
        frappe.get_doc(user_doc).insert(ignore_permissions=True)
        frappe.db.commit()

    def _cleanup(self):
        # Delete in reverse-dependency order
        emp = frappe.db.get_value("Employee", {"user_id": TEST_EMAIL}, "name")
        if emp:
            for ac in frappe.get_all("Activity Cost", filters={"employee": emp}, pluck="name"):
                frappe.delete_doc("Activity Cost", ac, force=True)
            frappe.delete_doc("Employee", emp, force=True)

        for supplier_name in (TEST_FULL_NAME, TEST_FIRST_NAME):
            if frappe.db.exists("Supplier", supplier_name):
                frappe.delete_doc("Supplier", supplier_name, force=True)

        if frappe.db.exists("User", TEST_EMAIL):
            frappe.delete_doc("User", TEST_EMAIL, force=True)

        frappe.db.commit()

    # ── Guard ─────────────────────────────────────────────────────────────────

    def test_raises_if_user_does_not_exist(self):
        frappe.delete_doc("User", TEST_EMAIL, force=True)
        frappe.db.commit()
        with self.assertRaises(frappe.ValidationError):
            create_engineer(
                email=TEST_EMAIL,
                first_name=TEST_FIRST_NAME,
                last_name=TEST_LAST_NAME,
                country="Taiwan",
                activity_type=TEST_ACTIVITY_TYPE,
                billing_rate=120,
                costing_rate=80,
            )

    # ── Happy path ────────────────────────────────────────────────────────────

    def test_creates_all_four_records(self):
        result = create_engineer(
            email=TEST_EMAIL,
            first_name=TEST_FIRST_NAME,
            last_name=TEST_LAST_NAME,
            country="Taiwan",
            activity_type=TEST_ACTIVITY_TYPE,
            billing_rate=120,
            costing_rate=80,
        )

        self.assertEqual(result["user"], TEST_EMAIL)
        self.assertEqual(result["supplier"], TEST_FULL_NAME)
        self.assertTrue(frappe.db.exists("Employee", result["employee"]))
        self.assertTrue(frappe.db.exists("Activity Cost", result["activity_cost"]))

    def test_employee_has_correct_fields(self):
        result = create_engineer(
            email=TEST_EMAIL,
            first_name=TEST_FIRST_NAME,
            last_name=TEST_LAST_NAME,
            country="Taiwan",
            activity_type=TEST_ACTIVITY_TYPE,
            billing_rate=120,
            costing_rate=80,
        )
        emp = frappe.get_doc("Employee", result["employee"])
        self.assertEqual(emp.employee_name, TEST_FULL_NAME)
        self.assertEqual(emp.user_id, TEST_EMAIL)
        self.assertEqual(emp.status, "Active")
        self.assertIsNotNone(emp.date_of_joining)

    def test_supplier_has_correct_fields(self):
        result = create_engineer(
            email=TEST_EMAIL,
            first_name=TEST_FIRST_NAME,
            last_name=TEST_LAST_NAME,
            country="Taiwan",
            activity_type=TEST_ACTIVITY_TYPE,
            billing_rate=120,
            costing_rate=80,
        )
        supplier = frappe.get_doc("Supplier", result["supplier"])
        self.assertEqual(supplier.supplier_type, "Individual")
        self.assertEqual(supplier.supplier_group, "Subcontractors")
        self.assertEqual(supplier.country, "Taiwan")
        self.assertEqual(supplier.default_currency, "USD")
        self.assertTrue(
            any(pu.user == TEST_EMAIL for pu in supplier.portal_users),
            "portal_users should include the new User",
        )

    def test_activity_cost_has_correct_rates(self):
        result = create_engineer(
            email=TEST_EMAIL,
            first_name=TEST_FIRST_NAME,
            last_name=TEST_LAST_NAME,
            country="Taiwan",
            activity_type=TEST_ACTIVITY_TYPE,
            billing_rate=120,
            costing_rate=80,
        )
        ac = frappe.get_doc("Activity Cost", result["activity_cost"])
        self.assertEqual(ac.billing_rate, 120)
        self.assertEqual(ac.costing_rate, 80)
        self.assertEqual(ac.activity_type, TEST_ACTIVITY_TYPE)

    # ── Critical invariant ───────────────────────────────────────────────────

    def test_supplier_name_equals_employee_full_name(self):
        # ERPNext links Timesheet (Employee) → Purchase Invoice (Supplier) by exact name match.
        # Breaking this breaks the whole invoicing flow.
        result = create_engineer(
            email=TEST_EMAIL,
            first_name=TEST_FIRST_NAME,
            last_name=TEST_LAST_NAME,
            country="Taiwan",
            activity_type=TEST_ACTIVITY_TYPE,
            billing_rate=120,
            costing_rate=80,
        )
        emp = frappe.get_doc("Employee", result["employee"])
        self.assertEqual(result["supplier"], emp.employee_name)

    # ── Role assignment ──────────────────────────────────────────────────────

    def test_role_profile_assigned_when_available(self):
        if not frappe.db.exists("Role Profile", "Engineer"):
            self.skipTest("Engineer Role Profile not present on this site.")

        create_engineer(
            email=TEST_EMAIL,
            first_name=TEST_FIRST_NAME,
            last_name=TEST_LAST_NAME,
            country="Taiwan",
            activity_type=TEST_ACTIVITY_TYPE,
            billing_rate=120,
            costing_rate=80,
        )
        user = frappe.get_doc("User", TEST_EMAIL)
        self.assertEqual(user.role_profile_name, "Engineer")

    def test_employee_role_fallback_when_no_role_profile(self):
        if frappe.db.exists("Role Profile", "Engineer"):
            self.skipTest("Engineer Role Profile exists; fallback path not exercised.")

        create_engineer(
            email=TEST_EMAIL,
            first_name=TEST_FIRST_NAME,
            last_name=TEST_LAST_NAME,
            country="Taiwan",
            activity_type=TEST_ACTIVITY_TYPE,
            billing_rate=120,
            costing_rate=80,
        )
        roles = set(
            frappe.get_all(
                "Has Role",
                filters={"parent": TEST_EMAIL, "parenttype": "User"},
                pluck="role",
            )
        )
        self.assertIn("Employee", roles)

    # ── Edge cases ───────────────────────────────────────────────────────────

    def test_last_name_is_optional(self):
        result = create_engineer(
            email=TEST_EMAIL,
            first_name=TEST_FIRST_NAME,
            country="Taiwan",
            activity_type=TEST_ACTIVITY_TYPE,
            billing_rate=120,
            costing_rate=80,
        )
        # No trailing space in Supplier name
        self.assertEqual(result["supplier"], TEST_FIRST_NAME)

    def test_idempotent_rerun_updates_rates_and_reuses_records(self):
        first = create_engineer(
            email=TEST_EMAIL, first_name=TEST_FIRST_NAME, last_name=TEST_LAST_NAME,
            country="Taiwan", activity_type=TEST_ACTIVITY_TYPE,
            billing_rate=120, costing_rate=80,
        )
        second = create_engineer(
            email=TEST_EMAIL, first_name=TEST_FIRST_NAME, last_name=TEST_LAST_NAME,
            country="Taiwan", activity_type=TEST_ACTIVITY_TYPE,
            billing_rate=150, costing_rate=100,
        )

        self.assertEqual(first["user"], second["user"])
        self.assertEqual(first["employee"], second["employee"])
        self.assertEqual(first["supplier"], second["supplier"])
        self.assertEqual(first["activity_cost"], second["activity_cost"])

        ac = frappe.get_doc("Activity Cost", second["activity_cost"])
        self.assertEqual(ac.billing_rate, 150)
        self.assertEqual(ac.costing_rate, 100)
