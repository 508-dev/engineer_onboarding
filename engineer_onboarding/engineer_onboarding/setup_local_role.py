"""
Local test setup: creates 508_Engineer role + permissions + Engineer Role Profile.

Mirrors prod's Employee-role permission set on a clean custom role so we can
test the Role Profile path without touching the built-in Employee role.

Run:
    bench --site frontend execute \
        engineer_onboarding.engineer_onboarding.setup_local_role.run

Undo:
    bench --site frontend execute \
        engineer_onboarding.engineer_onboarding.setup_local_role.teardown
"""
import frappe

ROLE = "508_Engineer"
ROLE_PROFILE = "Engineer"

# fmt: off
# Columns: doctype, if_owner,
#          select, read, write, create, delete,
#          submit, cancel, amend,
#          report, export, import_, print_, email, share
# Source: Role Permissions Manager screenshots (Employee role, confirmed 2026-04-20)
PERMISSIONS = [
    # Core engineer workflow
    ("Timesheet",         0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0),
    ("Purchase Invoice",  1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0),
    ("Project",           0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 1),
    ("Activity Cost",     0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0),
    ("Activity Type",     0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    # People / HR
    ("Employee",          0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 1),
    ("Supplier",          0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0),
    ("Customer",          0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1),
    ("Address",           0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0),
    ("Department",        0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    # Accounting / buying
    ("Sales Invoice",     0, 1, 1, 1, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1),
    ("Account",           0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0),
    ("Cost Center",       0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 1),
    ("Supplier Group",    0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0),
    ("Buying Settings",   1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0),
    ("Accounts Settings", 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0),
    ("Fiscal Year",       0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    # General
    ("Item",              0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0),
    ("Company",           0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    ("Page",              0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0),
    ("Call Log",          0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    ("Appointment",       0, 0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0),
    # Custom doctype — may not exist on vanilla ERPNext; skipped if absent
    ("Non Conformance",   0, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 1, 1, 0),
]
# fmt: on


def run():
    """Create 508_Engineer role, set permissions, create Engineer Role Profile."""

    # ── 1. Role ───────────────────────────────────────────────────────────────
    if not frappe.db.exists("Role", ROLE):
        frappe.get_doc({
            "doctype": "Role",
            "role_name": ROLE,
            "desk_access": 1,
        }).insert(ignore_permissions=True)
        print(f"[setup] Created role: {ROLE}")
    else:
        print(f"[setup] Role already exists: {ROLE}")

    # ── 2. Custom DocPerm records ─────────────────────────────────────────────
    keys = ("select", "read", "write", "create", "delete",
            "submit", "cancel", "amend",
            "report", "export", "import", "print", "email", "share")

    for row in PERMISSIONS:
        doctype, if_owner, *values = row

        if not frappe.db.exists("DocType", doctype):
            print(f"[setup] SKIP (DocType not on this site): {doctype}")
            continue

        # Wipe any existing entry for this role+doctype to keep it idempotent
        frappe.db.delete("Custom DocPerm", {"parent": doctype, "role": ROLE})

        perm_doc = {
            "doctype": "Custom DocPerm",
            "parent": doctype,
            "parenttype": "DocType",
            "parentfield": "permissions",
            "role": ROLE,
            "permlevel": 0,
            "if_owner": if_owner,
        }
        perm_doc.update(dict(zip(keys, values)))

        frappe.get_doc(perm_doc).insert(ignore_permissions=True)
        print(f"[setup] Permissions set: {doctype}")

    # ── 3. Role Profile ───────────────────────────────────────────────────────
    if frappe.db.exists("Role Profile", ROLE_PROFILE):
        rp = frappe.get_doc("Role Profile", ROLE_PROFILE)
        existing = [r.role for r in rp.roles]
        if ROLE not in existing:
            rp.append("roles", {"role": ROLE})
            rp.save(ignore_permissions=True)
            print(f"[setup] Role Profile '{ROLE_PROFILE}': added {ROLE}")
        else:
            print(f"[setup] Role Profile '{ROLE_PROFILE}' already has {ROLE}")
    else:
        frappe.get_doc({
            "doctype": "Role Profile",
            "role_profile": ROLE_PROFILE,
            "roles": [{"role": ROLE}],
        }).insert(ignore_permissions=True)
        print(f"[setup] Created Role Profile: {ROLE_PROFILE}")

    frappe.db.commit()
    frappe.clear_cache()
    print("\n[setup] Done. Run tests with:")
    print("  bench --site frontend run-tests --app engineer_onboarding")


def teardown():
    """Remove 508_Engineer role, its permissions, and the Engineer Role Profile."""

    # Role Profile
    if frappe.db.exists("Role Profile", ROLE_PROFILE):
        frappe.delete_doc("Role Profile", ROLE_PROFILE, force=True)
        print(f"[teardown] Deleted Role Profile: {ROLE_PROFILE}")

    # Custom DocPerm records
    count = frappe.db.count("Custom DocPerm", {"role": ROLE})
    frappe.db.delete("Custom DocPerm", {"role": ROLE})
    print(f"[teardown] Deleted {count} Custom DocPerm records for {ROLE}")

    # Role
    if frappe.db.exists("Role", ROLE):
        frappe.delete_doc("Role", ROLE, force=True)
        print(f"[teardown] Deleted role: {ROLE}")

    frappe.db.commit()
    frappe.clear_cache()
    print("[teardown] Done.")
