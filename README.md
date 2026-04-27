# Engineer Onboarding

A [Frappe](https://frappeframework.com/) custom app for [ERPNext](https://erpnext.com/) that automates engineer onboarding in one step.

Instead of manually creating 4 records across different modules, this app adds a **"Setup as Engineer"** button to the User form. Fill in the required fields, click Create, and the following records are created automatically:

- **User** — with role assigned (see Prerequisites)
- **Employee** — linked to the User
- **Supplier** — name matches Employee (required for Purchase Invoice matching), with the User added to portal_users
- **Activity Cost** — billing rate and costing rate for the engineer's activity type

## Prerequisites

Before installing, confirm the following exist on the target site:

### Option A — Engineer Role Profile (preferred)

Create a Role Profile named exactly **`Engineer`** in ERPNext (Settings > Role Profile > New).  
The app detects it automatically and assigns it to the new User.

> For 508.dev prod: the "Engineer" Role Profile already exists and assigns the `Employee` role.  
> See `engineer_onboarding_flow.md` § Role Architecture for the recommended long-term improvement.

### Option B — No Role Profile (fallback)

If no "Engineer" Role Profile exists, the app assigns the built-in **`Employee`** role directly.  
In this case, confirm the `Employee` role has been configured with the permissions engineers need:

| Document | Minimum permissions |
|----------|-------------------|
| Timesheet | Select, Read, Write, Create, Submit, Cancel, Amend |
| Purchase Invoice | Read, Write, Create (`Only If Creator` checked) |
| Project | Select, Read |
| Customer | Select, Read |
| Supplier | Select, Read, Write |
| Activity Type | Read |

Check via: **Settings > Role Permissions Manager**, filter by role = `Employee`.

### Other requirements

- A `Subcontractors` Supplier Group must exist (Buying > Supplier Group)
- At least one Activity Type must exist (Projects > Activity Type)

## Installation

```bash
cd frappe-bench
bench get-app https://github.com/508dev/engineer_onboarding
bench --site <your-site> install-app engineer_onboarding
bench build --app engineer_onboarding
```

## Usage

1. Go to **Settings > User**
2. Open an existing User record (or create a new one and save it first)
3. Click the **"Setup as Engineer"** button in the top-right button area
4. Fill in the dialog fields:

| Field | Required | Notes |
|-------|----------|-------|
| First Name | Yes | Auto-filled from User |
| Last Name | No | Auto-filled from User |
| Country | Yes | Used for Supplier country |
| Department | No | Assigned to Employee |
| Activity Type | Yes | Links to Activity Cost |
| Billing Rate (USD/hr) | Yes | Rate charged to the client |
| Costing Rate (USD/hr) | Yes | Rate paid to the engineer |

5. Click **Create**
6. A success message appears with links to all 4 created records

> The button is disabled (greyed out) if the User already has a linked Employee.

### Setting a password for the new engineer (local / no email)

```bash
bench --site <your-site> set-password <engineer-email> <password>
```

## How It Works

```
User ──(user_id)──► Employee ──(Activity Cost)──► billing_rate / costing_rate
 │                                                        │
 │                                                 activity_type
 │
 └──(portal_users)──► Supplier ◄──────── Purchase Invoice
                      (name = Employee Name)
```

The Supplier name is intentionally set to match the Employee name exactly — ERPNext links Timesheets (via Employee) to Purchase Invoices (via Supplier) by name match.

## Testing

### Automated tests (required before every change)

```bash
# One-time: allow tests on the site
bench --site <your-site> set-config allow_tests true

# Run the suite
bench --site <your-site> run-tests --app engineer_onboarding
```

Expected: `OK` with 9 passing tests (role tests skip on the path that isn't active on the current site).

Tests cover:
- Guard — error if User doesn't exist before calling setup
- Happy path — all four records created
- Correct fields on Employee / Supplier / Activity Cost
- Critical invariant: `Supplier.name == Employee.employee_name`
- Role Profile assigned when it exists on the site; `Employee` role as fallback
- `last_name` is optional
- Idempotency — re-running updates rates, doesn't create duplicates

### Manual testing

Confirm prerequisites exist:
- `http://localhost:8080/app/activity-type`
- `http://localhost:8080/app/supplier-group` (must have "Subcontractors")

**Happy path:**

1. Create User: `test.engineer@example.com`, First: `Test`, Last: `Engineer`, Save
2. Click **"Setup as Engineer"**, fill: Country = Taiwan, Activity Type = any, Billing = 120, Costing = 80
3. Click **Create** → green success message with 4 links

**Verify:**

| Record | What to check |
|--------|--------------|
| User | Has `Engineer` Role Profile or `Employee` role |
| Employee | `user_id` = engineer email, `date_of_joining` = today |
| Supplier | `supplier_group` = Subcontractors, `portal_users` includes the User |
| Activity Cost | Correct rates, linked to the Employee |

**Other scenarios:** idempotency (run twice, rates update, no duplicates), no last name, already-set-up button greyed out.

### API Test (curl)

```bash
curl -s -X POST "http://localhost:8080/api/method/engineer_onboarding.engineer_onboarding.onboarding_utils.create_engineer" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -b "sid=<your-session-id>" \
  --data-urlencode "email=test.engineer@example.com" \
  --data-urlencode "first_name=Test" \
  --data-urlencode "last_name=Engineer" \
  --data-urlencode "country=Taiwan" \
  --data-urlencode "activity_type=Engineering" \
  --data-urlencode "billing_rate=120" \
  --data-urlencode "costing_rate=80" \
  | python3 -m json.tool
```

## File Structure

```
engineer_onboarding/
├── engineer_onboarding/
│   ├── hooks.py                          # Injects JS into User doctype
│   ├── engineer_onboarding/
│   │   ├── onboarding_utils.py           # create_engineer() API
│   │   └── test_onboarding_utils.py      # Unit tests (must pass before merging)
│   └── public/
│       └── js/
│           └── user_onboarding.js        # "Setup as Engineer" button + dialog
└── pyproject.toml
```

## License

MIT
