# Copyright (c) 2024, Havenir and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Channel(Document):
	def validate(self):
		self.create_account()
		self.create_mode_of_payment()
	def create_account(self):
		company = frappe.get_doc("Company", self.company)
		abbr = company.abbr
		if self.channel_type == "Online Reservation":
			if not frappe.db.exists("Account", f"{self.channel_name} - {abbr}"):
				try:
					account = frappe.new_doc("Account")
					account.account_name = self.channel_name
					account.account_type = "Bank "
					account.root_type = "Asset"
					account.company = self.company
					account.parent_account = "Bank Accounts - {0}".format(abbr)
					account.insert()
					frappe.db.commit()
				except Exception as e:
					frappe.throw(f"Error creating account: {e}")
	def create_mode_of_payment(self):
		company = frappe.get_doc("Company", self.company)
		abbr = company.abbr
		if self.channel_type == "Online Reservation":
			if not frappe.db.exists("Mode of Payment", self.channel_name):
				try:
					mode_of_payment = frappe.new_doc("Mode of Payment")
					mode_of_payment.mode_of_payment = self.channel_name
					mode_of_payment.type = "Bank"
					#appened account
					mode_of_payment.append("accounts", {
						"company": self.company,
						"default_account": f"{self.channel_name} - {abbr}"
					})
					mode_of_payment.insert()
					frappe.db.commit()
				except Exception as e:
					frappe.throw(f"Error creating mode of payment: {e}")
	def on_trash(self):
		company = frappe.get_doc("Company", self.company)
		abbr = company.abbr
		if frappe.db.exists("Account", f"{self.channel_name} - {abbr}"):
			frappe.delete_doc("Account", f"{self.channel_name} - {abbr}")
		if frappe.db.exists("Mode of Payment", self.channel_name):
			frappe.delete_doc("Mode of Payment", self.channel_name)