# Copyright (c) 2023, Havenir and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class HotelCancellation(Document):
    def validate(self):
        room_doc = frappe.get_doc('Rooms', self.room)
        if room_doc.room_status != 'Checked In' and room_doc.check_in_id == self.check_in_id:
            frappe.throw('Room Status is not Checked In')

    def on_submit(self):
        room_doc = frappe.get_doc('Rooms',self.room)
        room_doc.db_set('room_status','Available')
        room_doc.db_set('check_in_id',None)
        check_in_doc = frappe.get_doc('Hotel Check In',self.check_in_id)
        check_in_doc.db_set('status','Cancelled')
