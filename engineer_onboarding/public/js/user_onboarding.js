// Engineer Onboarding — adds "Setup as Engineer" button on the User form

frappe.ui.form.on("User", {
	refresh: function (frm) {
		if (frm.is_new()) return;

		frappe.db.get_value("Employee", { user_id: frm.doc.name }, "name").then(r => {
			const already_setup = !!(r.message && r.message.name);

			const btn = frm.add_custom_button(__("Setup as Engineer"), function () {
			let d = new frappe.ui.Dialog({
				title: __("Setup as Engineer"),
				fields: [
					// Row 1
					{
						label: __("First Name"),
						fieldname: "first_name",
						fieldtype: "Data",
						reqd: 1,
						default: frm.doc.first_name,
					},
					{ fieldtype: "Column Break" },
					{
						label: __("Last Name"),
						fieldname: "last_name",
						fieldtype: "Data",
						default: frm.doc.last_name,
					},
					{ fieldtype: "Section Break" },
					// Row 2
					{
						label: __("Country"),
						fieldname: "country",
						fieldtype: "Link",
						options: "Country",
						reqd: 1,
					},
					{ fieldtype: "Column Break" },
					{
						label: __("Department"),
						fieldname: "department",
						fieldtype: "Link",
						options: "Department",
					},
					{ fieldtype: "Section Break", label: __("Rate Settings") },
					// Row 3
					{
						label: __("Activity Type"),
						fieldname: "activity_type",
						fieldtype: "Link",
						options: "Activity Type",
						reqd: 1,
					},
					{ fieldtype: "Column Break" },
					{
						label: __("Billing Rate (USD/hr)"),
						fieldname: "billing_rate",
						fieldtype: "Currency",
						reqd: 1,
						description: __("Rate charged to the client"),
					},
					{ fieldtype: "Column Break" },
					{
						label: __("Costing Rate (USD/hr)"),
						fieldname: "costing_rate",
						fieldtype: "Currency",
						reqd: 1,
						description: __("Rate paid to the engineer"),
					},
				],
				primary_action_label: __("Create"),
				primary_action: function () {
					const values = d.get_values();
					if (!values) return;

					d.disable_primary_action();

					frappe.call({
						method: "engineer_onboarding.engineer_onboarding.onboarding_utils.create_engineer",
						args: {
							email: frm.doc.name,
							first_name: values.first_name,
							last_name: values.last_name,
							country: values.country,
							activity_type: values.activity_type,
							billing_rate: values.billing_rate,
							costing_rate: values.costing_rate,
							department: values.department || null,
						},
						freeze: true,
						freeze_message: __("Setting up engineer..."),
						callback: function (r) {
							if (r.exc) {
								d.enable_primary_action();
								return;
							}

							const res = r.message;
							d.hide();

							frappe.msgprint({
								title: __("Engineer Setup Complete"),
								indicator: "green",
								message: `
									<b>${__("Records created:")}</b><br>
									${__("User")}: <a href="/app/user/${res.user}">${res.user}</a><br>
									${__("Employee")}: <a href="/app/employee/${res.employee}">${res.employee}</a><br>
									${__("Supplier")}: <a href="/app/supplier/${res.supplier}">${res.supplier}</a><br>
									${__("Activity Cost")}: <a href="/app/activity-cost/${res.activity_cost}">${res.activity_cost}</a>
								`,
							});
						},
					});
				},
			});

			d.show();
			});

			if (already_setup) {
				btn.prop("disabled", true).css("opacity", "0.5").attr("title", __("Engineer already set up"));
			}
		}); // frappe.db.get_value
	},
});
