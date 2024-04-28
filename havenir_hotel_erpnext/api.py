import frappe
from frappe.model.document import Document
from erpnext.accounts.utils import get_balance_on
import json

@frappe.whitelist()
def get_sales_invoice(guest):
    invoices = frappe.db.sql(f"""  SELECT name FROM 'tabSales Inovice' WHERE customer={guest} """, as_dict=True)
    frappe.msgprint(invoices)
    # return invoices

@frappe.whitelist()
def get_unpaid():
    #get all guests
    guests = frappe.db.get_list('Hotel Guests', fields=['name', 'balance'])
    for guest in guests:
        balance = get_balance_on(
            party_type='Customer',
            party=guest.name
        )
        guest.balance = balance
        guest.save()
@frappe.whitelist()
def check_in(doc):
    doc = frappe.get_doc("Reservation", doc)
    doc.db_set('status', 'To Check In')
    for room in doc.rooms:
        if room.room_status == 'Checked In':
            frappe.throw(f'Room {room.room_no} is already checked in')
    check_in_doc = frappe.new_doc('Hotel Check In')
    check_in_doc.guest_id = doc.guest_id
    check_in_doc.check_in = doc.arrival_date
    check_in_doc.guest_name = doc.guest_name
    check_in_doc.posting_date = nowdate()
    check_in_doc.duration = (getdate(doc.departure) - getdate(doc.arrival_date)).days
    check_in_doc.channel = doc.channel
    check_in_doc.company = doc.company
    for room in doc.rooms:
        check_in_doc.append('rooms', {
            'room_no': room.room_no
        })
    check_in_doc.save()
    check_in_doc.submit()
    doc.status = 'Checked In'
    doc.save()
    

    # return invoices
@frappe.whitelist()
def create_invoice(doc, method=None):
    doc = frappe.get_doc("Reservation", doc)
    if doc.invoice_created:
        frappe.msgprint("Invoice already created for this reservation")
    else:
        sales_invoice_doc = frappe.new_doc("Sales Invoice")
        company = frappe.get_doc("Company", doc.company)
        sales_invoice_doc.discount_amount = 0
        sales_invoice_doc.customer = doc.guest_id
        sales_invoice_doc.custom_reservation_id = doc.name
        sales_invoice_doc.due_date = doc.departure
        sales_invoice_doc.debit_to = company.default_receivable_account

        total_amount = 0
        for room in doc.rooms:
            room_price = room.price
            total_amount += float(room_price)
            sales_invoice_doc.append(
                "items",
                {
                    "item_code": f'Room - {room.room_no}',
                    "qty": float(doc.duration),
                    "rate": float(room_price),
                    "amount": float(room_price)*float(doc.duration),
                },
            )
        sales_invoice_doc.insert(ignore_permissions=True)
        sales_invoice_doc.submit()
        frappe.db.set_value('Reservation', doc.name, 'invoice_created', 1)

    @frappe.whitelist()
    def check_in_reservation(source_name, target_doc=None):
        reservation = frappe.get_doc('Reservation', source_name)
        for room in reservation.rooms:
            room_doc = frappe.get_doc('Rooms', room.room_no)
            room_doc.append('reservations', {
                'reservation_id': reservation.name,
                'arrival_date': reservation.arrival_date,
                'departure': reservation.departure,
                'guest_name': reservation.guest_name,
            })
            room_doc.save()
        reservation.status = 'To Check In'
        reservation.save()
    
    #return a list of reservation
@frappe.whitelist()
def get_reservation():
    return frappe.get_list('Reservation')
    #return a list of rooms
@frappe.whitelist()
def get_rooms():
    return frappe.get_list('Rooms', fields=['*'])

#return a list of Check In
@frappe.whitelist()
def get_check_in():
    return frappe.get_list('Hotel Check In', fields=['*'])

@frappe.whitelist()
def create_daily_report():
    check_in = frappe.db.count('Hotel Check In', {'check_in': frappe.utils.today()})
    available_rooms = frappe.db.count('Rooms', {'room_status': 'Available'})
    checked_in = frappe.db.count('Rooms', {'room_status': 'Checked In'})
    daily_report = frappe.new_doc("Daily Report")
    daily_report.date = frappe.utils.today()
    daily_report.bookings = check_in
    daily_report.available_rooms = available_rooms
    daily_report.checked_in = checked_in
    daily_report.save()
    frappe.db.commit()
    return checked_in

@frappe.whitelist()
def create_work_order(doc, method=None):
    inv = frappe.get_doc("Sales Invoice", doc)
    for item in inv.items:
        item_doc = frappe.get_doc("Item", item.item_code)
        bom = frappe.get_list('BOM', filters={'item': item.item_code, 'is_default': 1}, fields=['name'])        
        if bom:
            work_order = frappe.new_doc("Work Order")
            work_order.production_item = item.item_code
            work_order.qty = item.qty
            work_order.bom_no = bom[0].name
            work_order.skip_transfer = 1
            work_order.fg_warehouse = frappe.get_value('BOM', bom[0].name, 'custom_fg_warehouse')
            work_order.insert(ignore_permissions=True)
            work_order.save()
            work_order.submit()
            frappe.db.commit()

