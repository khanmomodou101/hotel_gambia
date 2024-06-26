// Copyright (c) 2023, Havenir and contributors
// For license information, please see license.txt

frappe.ui.form.on('Hotel Cancellation', {
	setup: function(frm) {
		// setting query for rooms to be visible in list
		frm.set_query("room", function(doc) {
			return {
				filters: {
					room_status: "Checked In"
				}
			};
		});
	}
});
