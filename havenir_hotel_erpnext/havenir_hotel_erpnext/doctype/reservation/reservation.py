# Copyright (c) 2024, Havenir and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import datetime, add_to_date, nowdate, getdate

class Reservation(Document):
	def validate(self):

		self.validate_room()
		#check if arrival date is not in the past
		if getdate(self.arrival_date) < getdate(nowdate()):
			frappe.throw('Arrival date must not be in the past')
		#check if departure date is not in the past
		if getdate(self.departure) < getdate(nowdate()):
			frappe.throw('Departure date must not be in the past')
		#check if departure date is not less than arrival date
		if getdate(self.departure) < getdate(self.arrival_date):
			frappe.throw('Departure date must not be less than arrival date')
	
	

	def on_submit(self):
		self.reserve_room()
		self.status = 'To Check In'
		doc = frappe.get_doc('Reservation', self.name)
		doc.db_set('status', 'To Check In')

		#remove reservation from rooms
			
	#set check the reserved field to true
	def reserve_room(self):
		for room in self.rooms:
			room = frappe.get_doc('Rooms', room.room_no)
			room.append('reservations', {
				'reservation_id': self.name,
				'arrival_date': self.arrival_date,
				'departure': self.departure,
				'guest_name': self.guest_name,
			})
			room.save()

	#checkif room is not reserved and not checked in
	# def validate_room(self):
	# 	for room in self.rooms:
	# 		room = frappe.get_doc('Rooms', room.room_no)
	# 		reservations = room.get('reservations')
	# 		#validate check in date
	# 		if room.room_status == 'Checked In':
	# 			check_in_date = frappe.db.get_value('Hotel Check In', room.check_in_id, 'check_in')
	# 			check_out_date = frappe.db.get_value('Hotel Check In', room.check_in_id, 'check_out')
				
	# 			if getdate(check_in_date) <= getdate(self.arrival_date) and getdate(self.arrival_date) <= getdate(check_out_date):
	# 				frappe.throw(f'Room {room.name} is already checked in for the selected date')
	# 		if reservations:
	# 				for reservation in reservations:
	# 					if getdate(reservation.arrival_date) <= getdate(self.arrival_date) and getdate(self.arrival_date) <= getdate(reservation.departure):
	# 						frappe.throw(f'Room {room.name} is already reserved for the selected date')
	
	def validate_room(self):
		for room in self.rooms:
			room_doc = frappe.get_doc('Rooms', room.room_no)
			reservations = room_doc.get('reservations')
			if room_doc.room_status == 'Checked In':
				check_in_date = frappe.db.get_value('Hotel Check In', room_doc.check_in_id, 'check_in')
				check_out_date = frappe.db.get_value('Hotel Check In', room_doc.check_in_id, 'check_out')
				if getdate(check_in_date) <= getdate(self.arrival_date) <= getdate(check_out_date):
					frappe.throw(f'Room {room_doc.name} is already checked in for the selected date')
			if reservations:
				reservation_ids = [reservation.reservation_id for reservation in reservations]
				if self.reservation_id not in reservation_ids:
					for reservation in reservations:
						if getdate(reservation.arrival_date) <= getdate(self.arrival_date) <= getdate(reservation.departure):
							frappe.throw(f'Room {room_doc.name} is already reserved for the selected date')
						elif getdate(self.arrival_date) < getdate(reservation.arrival_date) and getdate(self.departure_date) > getdate(reservation.departure):
							frappe.throw(f'Room {room_doc.name} is already reserved during this period')

	#check if invoice is created against this reservation
	def check_invoice(self):
		invoice = frappe.get_list('Sales Invoice', filters={
			'custom_reservation_id': self.name
		})
		if invoice:
			return True
		else:
			return False
	def on_cancel(self):
		#remove reservation from rooms
		for room in self.rooms:
			room = frappe.get_doc('Rooms', room.room_no)
			reservations = room.get('reservations')
			for reservation in reservations:
				if reservation.reservation_id == self.name:
					room.remove(reservation)
					room.save()

#get reservation information
@frappe.whitelist()
def get_rooms(doc):
	rooms = frappe.get_doc('Reservation', doc.name)
	return rooms.get('rooms')
