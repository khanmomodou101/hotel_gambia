// Copyright (c) 2024, Havenir and contributors
// For license information, please see license.txt

// let d = frappe.new_doc("Journal Entry", {"voucher_type": "Bank Entry"}, doc => {
// 	doc.posting_date = frappe.datetime.get_today();
// 	let row = frappe.model.add_child(doc, "accounts");
// 	row.account = 'Bank - A';
// 	row.account_currency = 'USD';
// 	row.debit_in_account_currency = 100.0;
// 	row.credit_in_account_currency = 0.0;
// });

frappe.ui.form.on('Reservation', {

	//add a button to check in the reservation
	after_save: function(frm) {
		
	},

			
	refresh: function(frm) {
		//only show the button if the document statuse is To Check In

		//check if the reservation is not checked in and not new and not cancelled
		if (!frm.doc.checked_in && !frm.doc.is_new()) {


		frm.add_custom_button(__('Check In'), function(){
		//get the rooms from the reservation

		

		let d = frappe.new_doc("Hotel Check In", {
			'guest_id': frm.doc.guest_id,
			'posting_date': frm.doc.posting_date,
			'check_in_date': frm.doc.arrival_date,
			'channel': frm.doc.channel,
			'reservation_id': frm.doc.name,
		}, doc => {
			//add the rooms to the hotel check in
			// console.log(frm.doc.rooms[0].room_no);
			for (var i = 0; i < frm.doc.rooms.length; i++) {
				// delete default row
				frappe.model.clear_table(doc, "rooms");
				let row = frappe.model.add_child(doc, "rooms");
				row.room_no = frm.doc.rooms[i].room_no;
				row.room_type = frm.doc.rooms[i].room_type;
				row.price = frm.doc.rooms[i].price;
				row.occupancy = frm.doc.rooms[i].occupancy;
			}
		});
		d.show();


		
			
		}, __("Make"));	
	}			
				}
			});

			
			