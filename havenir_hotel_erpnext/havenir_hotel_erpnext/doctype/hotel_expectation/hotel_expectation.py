# -*- coding: utf-8 -*-
# Copyright (c) 2020, Havenir and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.core.doctype.sms_settings.sms_settings import send_sms


class HotelExpectation(Document):
    def validate(self):
        for room in self.rooms:
            room_doc = frappe.get_doc('Rooms', room.room_no)
            if room_doc.room_status != 'Available':
                frappe.throw('Room {} is not Available'.format(room.room_no))

    def on_submit(self):
        # self.create_sales_invoice()
        self.status = 'To Check In'
        # doc = frappe.get_doc('Hotel Check In', self.name)
        # doc.db_set('status', 'To Check Out')
        for room in self.rooms:
            room_doc = frappe.get_doc('Rooms', room.room_no)
            room_doc.db_set('expectation_id', self.name)
            room_doc.db_set('room_status', 'Expected')
            room_doc.db_set('expectation_date', self.expectation_date)
        # send_payment_sms(self)

    def on_cancel(self):
        self.status = "Cancelled"
        # doc = frappe.get_doc('Hotel Check In', self.name)
        # doc.db_set('status', 'Cancelled')
        for room in self.rooms:
            room_doc = frappe.get_doc('Rooms', room.room_no)
            room_doc.db_set('expectation_id', None)
            room_doc.db_set('room_status', 'Available')
    @frappe.whitelist()
    def get_room_price(self, room):
        room_price = frappe.get_value('Rooms', {
            'room_number': room
        }, [
            'price'
        ])
        return room_price
    

    def create_sales_invoice(self):
        sales_invoice_doc = frappe.new_doc("Sales Invoice")
        company = frappe.get_doc("Company", self.company)
        sales_invoice_doc.discount_amount = 0
        sales_invoice_doc.customer = self.guest_id
        sales_invoice_doc.check_in_id = self.name
        sales_invoice_doc.check_in_date = self.check_in
        sales_invoice_doc.due_date = frappe.utils.data.today()
        sales_invoice_doc.debit_to = company.default_receivable_account

        total_amount = 0
        for room in self.rooms:
            room_price = room.price
            total_amount += float(room_price)  # Convert to float before addition
            sales_invoice_doc.append(
                "items",
                {
                    "item_code": room.room_no,
                    "qty": float(self.duration),  # Convert to float before assignment
                    "rate": float(room_price),  # Convert to float before assignment
                    "amount": float(room_price) * float(self.duration),  # Convert to float before multiplication
                },
            )
        sales_invoice_doc.insert(ignore_permissions=True)
        sales_invoice_doc.submit()


    

def send_payment_sms(self):
    sms_settings = frappe.get_doc('SMS Settings')
    if sms_settings.sms_gateway_url:
        msg = 'Dear '
        msg += self.guest_name
        msg += ''',\nWe are delighted that you have selected our hotel. The entire team at the Hotel PakHeritage welcomes you and trust your stay with us will be both enjoyable and comfortable.\nRegards,\nHotel Management'''
        send_sms([self.contact_no], msg = msg)
