import frappe
from frappe import _
from frappe.utils import today


@frappe.whitelist()
def create_engineer(
    email,
    first_name,
    last_name=None,
    country=None,
    activity_type=None,
    billing_rate=0,
    costing_rate=0,
    department=None,
):
    """
    Completes onboarding for an existing User:
      1. User     — sets Role Profile / role if not already configured
      2. Employee — creates if not exists, linked to User
      3. Supplier — creates if not exists, name = Employee name, portal_users = User
      4. Activity Cost — creates or updates billing/costing rates

    Returns a dict with the names of all created/found records.
    """
    full_name = " ".join(filter(None, [first_name, last_name]))
    results = {}

    # ── 1. User ──────────────────────────────────────────────────────────────
    # Prefer the "Engineer" Role Profile (prod convention, confirmed 2026-04-20
    # with Caleb). If it doesn't exist on the site, fall back to assigning the
    # "Employee" role directly — prod's Employee role has been extended with the
    # permissions engineers need (Timesheet, Project, Supplier, Purchase Invoice).
    #
    # TODO: the current setup mutates the built-in Employee role, which can bleed
    # permissions to non-engineer employees. Recommended improvement: create a
    # custom role (e.g. 508_Engineer) and point the Role Profile at that instead.
    # See engineer_onboarding_flow.md § Role Architecture for full discussion.
    # The button only appears on existing User records, so User is guaranteed to
    # exist here. Raise early if called directly via API with a bad email.
    if not frappe.db.exists("User", email):
        frappe.throw(_("User {0} does not exist. Create the User first, then run Setup as Engineer.").format(email))

    user = frappe.get_doc("User", email)

    # Ensure the user has the correct role even if the admin forgot to set it.
    #
    # Priority:
    #   1. Already has "Engineer" Role Profile → nothing to do
    #   2. "Engineer" Role Profile exists on this site → assign it
    #   3. Fallback → assign "Employee" role directly (prod's Employee role carries
    #      the engineer permission set; see engineer_onboarding_flow.md § Role Architecture)
    if user.role_profile_name != "Engineer":
        if frappe.db.exists("Role Profile", "Engineer"):
            user.role_profile_name = "Engineer"
        elif not any(r.role == "Employee" for r in user.roles):
            user.append("roles", {"role": "Employee"})
        user.save(ignore_permissions=True)

    results["user"] = user.name

    # ── 2. Employee ───────────────────────────────────────────────────────────
    existing_employee = frappe.db.get_value("Employee", {"user_id": email}, "name")
    if existing_employee:
        employee = frappe.get_doc("Employee", existing_employee)
    else:
        employee_doc = {
            "doctype": "Employee",
            "first_name": first_name,
            "last_name": last_name or "",
            "employee_name": full_name,
            "user_id": email,
            "status": "Active",
            "date_of_joining": today(),
            "company": frappe.defaults.get_global_default("company"),
        }
        if department:
            employee_doc["department"] = department

        employee = frappe.get_doc(employee_doc)
        employee.flags.ignore_mandatory = True  # gender/date_of_birth are personal data, filled by employee later
        employee.insert(ignore_permissions=True)

    results["employee"] = employee.name

    # ── 3. Supplier ───────────────────────────────────────────────────────────
    if frappe.db.exists("Supplier", full_name):
        supplier = frappe.get_doc("Supplier", full_name)
        # Make sure portal_users includes this user
        portal_user_exists = any(pu.user == email for pu in supplier.portal_users)
        if not portal_user_exists:
            supplier.append("portal_users", {"user": email})
            supplier.save(ignore_permissions=True)
    else:
        supplier = frappe.get_doc({
            "doctype": "Supplier",
            "supplier_name": full_name,
            "supplier_type": "Individual",
            # default group for new suppliers, can be changed later by admin
            "supplier_group": "Subcontractors",
            "country": country,
            "default_currency": "USD",
            "portal_users": [{"user": email}],
        })
        supplier.insert(ignore_permissions=True)

    results["supplier"] = supplier.name

    # ── 4. Activity Cost ──────────────────────────────────────────────────────
    existing_ac = frappe.db.get_value(
        "Activity Cost",
        {"employee": employee.name, "activity_type": activity_type},
        "name",
    )
    if existing_ac:
        ac = frappe.get_doc("Activity Cost", existing_ac)
        ac.billing_rate = billing_rate
        ac.costing_rate = costing_rate
        ac.save(ignore_permissions=True)
    else:
        ac = frappe.get_doc({
            "doctype": "Activity Cost",
            "employee": employee.name,
            "activity_type": activity_type,
            "billing_rate": billing_rate,
            "costing_rate": costing_rate,
        })
        ac.insert(ignore_permissions=True)

    results["activity_cost"] = ac.name

    frappe.db.commit()
    return results
