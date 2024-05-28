# -*- coding: utf-8 -*-
# Copyright (c) 2020, Havenir and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.core.doctype.sms_settings.sms_settings import send_sms
from datetime import datetime, timedelta
from frappe.utils import add_to_date, nowdate, getdate, date_diff, time_diff_in_hours



class HotelCheckIn(Document):
    def validate(self):
        #cehck if booking date is not in the past
        # if getdate(self.check_in) < getdate(nowdate()):
        #     frappe.throw('Check-In date must not be in the past')
        
        #checkif check in is per nigth or per hour
        if self.stay_type == 'Per Night':
            if getdate(self.check_out) < getdate(self.check_in):
                frappe.throw('Check-Out date must not be in the past')
            

        for room in self.rooms:
            room_doc = frappe.get_doc('Rooms', room.room_no)
            if room_doc.room_status == 'Checked In' :
                frappe.throw('Room {} is not Available'.format(room.room_no))
        self.validate_room()

           

    def validate_room(self):
            for room in self.rooms:
                room_doc = frappe.get_doc('Rooms', room.room_no)
                reservations = room_doc.get('reservations')
                if reservations:
                    reservation_ids = [reservation.reservation_id for reservation in reservations]
                    if self.reservation_id not in reservation_ids:
                        for reservation in reservations:
                            if getdate(reservation.arrival_date) <= getdate(self.check_in) <= getdate(reservation.departure):
                                frappe.throw(f'Room {room_doc.name} is already reserved for the selected date')
                            elif getdate(self.check_in) < getdate(reservation.arrival_date) and getdate(self.check_out) > getdate(reservation.departure):
                                frappe.throw(f'Room {room_doc.name} is already reserved during this period')

    def on_submit(self):
        if self.reservation_id:
            frappe.db.set_value('Reservation', self.reservation_id, 'checked_in', 1)
            frappe.db.set_value('Reservation', self.reservation_id, 'status', 'Checked In')

        self.create_sales_invoice()
        channel = frappe.get_doc('Channel', self.channel)
        if channel.channel_type == 'Online Reservation':
            self.create_payment_entry()
        
        self.add_guest_to_in_house_guest()
        self.status = 'To Check Out'
        doc = frappe.get_doc('Hotel Check In', self.name)
        doc.db_set('status', 'To Check Out')
        for room in self.rooms:
            room_doc = frappe.get_doc('Rooms', room.room_no)
            room_doc.db_set('check_in_id', self.name)
            room_doc.db_set('room_status', 'Checked In')
        
        if self.reservation_id:
             for room in self.rooms:
                room = frappe.get_doc('Rooms', room.room_no)
                reservations = room.get('reservations')
                for reservation in reservations:
                     if reservation.reservation_id == self.reservation_id:
                        room.remove(reservation)
                        room.save()

            
        
    def on_cancel(self):
        self.status = "Cancelled"
        doc = frappe.get_doc('Hotel Check In', self.name)
        doc.db_set('status', 'Cancelled')
        for room in self.rooms:
            room_doc = frappe.get_doc('Rooms', room.room_no)
            room_doc.db_set('check_in_id', None)
            room_doc.db_set('room_status', 'Available')
    # @frappe.whitelist()
    # def get_room_price(self, room):
    #     room_price = frappe.get_value('Rooms', {
    #         'room_number': room
    #     }, [
    #         'price'
    #     ])
    #     return room_price
    
    
           
    def calculate_discount(self):
        discount_amount = self.discount_amount
        discount_percentage = self.discount_percentage
        discount_amount = 0
        if self.discount_percentage:
            discount_amount = (self.total_amount * self.discount_percentage) / 100
        elif self.discount_amount:
            discount_amount = self.discount_amount
        else:
            discount_amount = 0
        return discount_amount        

    def create_sales_invoice(self):
        sales_invoice_doc = frappe.new_doc("Sales Invoice")
        company = frappe.get_doc("Company", self.company)
        sales_invoice_doc.discount_amount = 0
        sales_invoice_doc.customer = self.guest_id
        sales_invoice_doc.check_in_id = self.name
        sales_invoice_doc.check_in_date = self.check_in
        sales_invoice_doc.due_date = self.check_out
        sales_invoice_doc.debit_to = company.default_receivable_account

        total_amount = 0
        for room in self.rooms:
            item_doc = frappe.get_doc('Item', f'Room - {room.room_no}')
            default_income_account = None
            for item_default in item_doc.item_defaults:
                if item_default.company == self.company:
                    if item_default.income_account:
                        default_income_account = item_default.income_account
                    else:
                        default_income_account = company.default_income_account
            room_price = room.price
            total_amount += float(room_price)  # Convert to float before addition
            sales_invoice_doc.append(
                "items",
                {
                    "item_code": f'Room - {room.room_no}',
                    "qty": float(self.duration),  # Convert to float before assignment
                    "rate": room.price,  # Convert to float before assignment
                    "amount": float(room.price) * float(self.duration),  # Convert to float before multiplication
                },
            )
        sales_invoice_doc.apply_discount_on = 'Grand Total'
        sales_invoice_doc.discount_amount = self.calculate_discount()
        sales_invoice_doc.insert(ignore_permissions=True)
        sales_invoice_doc.submit()
        frappe.db.commit()

#add guest to in hosue guest
    def add_guest_to_in_house_guest(self):
        #check if user is already in
    
        if not frappe.db.exists("Guest In House", {'email': self.guest_id}):
            rooms = 'Room '
            for room in self.rooms:
                rooms = f'{rooms}, {room.room_no}'
            doc = frappe.get_doc({
                "doctype": "Guest In House",
                "guest_name": self.guest_name,
                "email": self.guest_id,
                "room": rooms,
                "check_in_date": self.check_in,
                "departure": self.check_out,
                "check_in_id": self.name
            })
            doc.insert()
            doc.save()
        else:
            doc = frappe.get_doc("Guest In House", {'email': self.guest_id})
            rooms = f'{doc.room} '
            for room in self.rooms:
                rooms = f'{rooms}, {room.room_no}'
            doc.db_set('room', rooms)


    #calculate the check out date based on the check in date and duration and the unit of measurement
    def calculate_check_out_date(self):
        if self.check_in and self.duration:
            if self.unit_of_measurement == 'Days':
                return add_to_date(self.check_in, days=self.duration)
            return add_to_date(self.check_in, self.duration, self.unit_of_measurement)
    #create payment entry
    def create_payment_entry(self):
        channel = frappe.get_doc('Channel', self.channel)
        company = frappe.get_doc('Company', self.company)
        abbreviation = company.abbr
        inv = frappe.get_doc('Sales Invoice', {'check_in_id': self.name})


        payment = frappe.new_doc('Payment Entry')
        payment.payment_type = 'Receive'
        payment.company = self.company
        payment.posting_date = self.check_in
        payment.payment_date = self.check_in
        payment.party_type = 'Customer'
        payment.party =  self.guest_id
        payment.mode_of_payment = self.channel
        payment.paid_from = f'Debtors - {abbreviation}'
        payment.paid_to = f'{channel.channel_name} - {abbreviation}'
        payment.paid_amount = inv.total
        payment.received_amount = inv.total
        #append reference sales invoice
        payment.append('references', {
            'reference_doctype': 'Sales Invoice',
            'reference_name': inv.name,
            'total_amount': inv,
            'outstanding_amount': inv.outstanding_amount,
            'allocated_amount': inv.total,
            

        })
        payment.total_allocated_amount = inv.total
        payment.reference_no = inv.name
        payment.reference_date = self.check_in
        payment.insert()
        payment.submit()
        frappe.db.commit()


    
    #validate room availability
def send_payment_sms(self):
    sms_settings = frappe.get_doc('SMS Settings')
    if sms_settings.sms_gateway_url:
        msg = 'Dear '
        msg += self.guest_name
        msg += ''',\nWe are delighted that you have selected our hotel. The entire team at the Hotel PakHeritage welcomes you and trust your stay with us will be both enjoyable and comfortable.\nRegards,\nHotel Management'''
        send_sms([self.contact_no], msg=msg)

@frappe.whitelist()
def extend_stay(doc, check_out):

    duration = int(frappe.get_value('Hotel Check In', doc, 'duration'))
    stay_type = frappe.get_value('Hotel Check In', doc, 'stay_type')
    new_diff = 0
    if stay_type == 'Per Night':
        check_in = frappe.get_value('Hotel Check In', doc, 'check_in')
        new_diff = int(date_diff(getdate(check_out), check_in))
        if new_diff < 0:
            frappe.throw('Check-Out date must not be in the past')
        elif new_diff <= duration:
            frappe.throw('Duration must be greater than the previous duration')
        
        else:
            frappe.db.update('Hotel Check In', doc, 'duration', new_diff)
            frappe.db.update('Hotel Check In', doc, 'check_out', check_out)
            frappe.db.commit()
    else:
        check_in = frappe.get_value('Hotel Check In', doc, 'check_in_time')
        new_diff = int(time_diff_in_hours(check_out, check_in))
        if new_diff < 0:
            frappe.throw('Check-Out time must be greater than Check-In time')
        elif new_diff <= duration:
            frappe.throw('Duration must be greater than the previous duration')
        else:    
            frappe.db.update('Hotel Check In', doc, 'check_out_time', check_out)
            frappe.db.update('Hotel Check In', doc, 'duration', new_diff)
            frappe.db.commit()
    
    #create extra charges and invoice
    check_in_doc = frappe.get_doc('Hotel Check In', doc)
    sales_invoice_doc = frappe.new_doc("Sales Invoice")
    company = frappe.get_doc("Company", frappe.db.get_value('Hotel Check In', doc, 'company'))
    sales_invoice_doc.discount_amount = 0
    sales_invoice_doc.customer = frappe.db.get_value('Hotel Check In', doc, 'guest_id')
    sales_invoice_doc.check_in_id = doc
    sales_invoice_doc.check_in_date = frappe.db.get_value('Hotel Check In', doc, 'check_in')
    sales_invoice_doc.due_date = check_out
    sales_invoice_doc.debit_to = company.default_receivable_account
    total_amount = 0
    for room in check_in_doc.rooms:
        item_doc = frappe.get_doc('Item', f'Room {room_no}')
        default_income_account = None
        for item_default in item_doc.item_defaults:
            if item_default.company == self.company:
                if item_default.income_account:
                    default_income_account = item_default.income_account
                else:
                    default_income_account = company.default_income_account
        room_price = room.price
        total_amount += float(room_price)  # Convert to float before addition
        sales_invoice_doc.append(
            "items",
                {
                    "item_code": f'Room - {room.room_no}',
                    "qty": float(new_diff),  # Convert to float before assignment
                    "rate": room.price,  # Convert to float before assignment
                    "amount": float(room.price) * float(new_diff),  # Convert to float before multiplication
                    'income_account': default_income_account
                },
            )
    sales_invoice_doc.insert(ignore_permissions=True)
    sales_invoice_doc.submit()
    frappe.msgprint('Check-Out date has been extended to {}'.format(check_out))


        
   
    
#new duration