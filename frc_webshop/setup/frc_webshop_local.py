# Copyright (c) 2026, Muhammad Yusuf Tri Daryanto
# License: MIT

"""Idempotent local Webshop setup for the 48 FRC Customers on erp.localhost."""

from __future__ import annotations

import os
import re

import frappe
from frappe.utils.user import add_role

SITE = "erp.localhost"
COMPANY = "PT. JUARA ROTI INDONESIA"
FRC_GROUP = "Outlet Franchise"
POLICY_FIELD = "custom_payment_release_policy"
FULL_PAYMENT = "Full Payment"
LEGACY = "Legacy (No Gate)"
PRICE_LIST = "Harga Outlet"
WEB_ITEMS = {
	"PJO2601": "Gudang Barang Jadi - JURI",
	"PJ260010": "Gudang Barang Jadi - JURI",
}
DRY_PRICE = 25000.0
PASSWORD_ENV = "W55_FRC_PASSWORD"


def setup(password: str | None = None) -> dict:
	"""Configure Webshop, portal users, policies, and published items."""
	_guard_site()
	password = password or os.environ.get(PASSWORD_ENV)
	if not password:
		raise ValueError(f"Set {PASSWORD_ENV} or pass password= to setup().")

	settings = frappe.get_doc("Webshop Settings")
	settings.update(
		{
			"enabled": 1,
			"enable_checkout": 0,
			"save_quotations_as_draft": 0,
			"price_list": PRICE_LIST,
			"company": COMPANY,
		}
	)
	settings.flags.ignore_permissions = True
	settings.save()

	frcs = _frc_customers()
	for customer in frcs:
		frappe.db.set_value("Customer", customer["name"], POLICY_FIELD, FULL_PAYMENT)
		email = _email(customer["name"])
		_ensure_user(email, _first_name(customer["customer_name"]), password)
		_ensure_contact(email, _first_name(customer["customer_name"]), customer["name"])
		_ensure_portal_user(customer["name"], email)
	_publish_items()
	_ensure_dry_price()
	frappe.db.commit()
	return {"frc_customers": len(frcs), "web_items": len(WEB_ITEMS)}


def teardown() -> dict:
	"""Undo the local FRC Webshop setup. Keeps native documents untouched."""
	_guard_site()
	frcs = _frc_customers()
	for customer in frcs:
		email = _email(customer["name"])
		_ensure_portal_user_removed(customer["name"], email)
		frappe.db.set_value("Customer", customer["name"], POLICY_FIELD, LEGACY)
		for doctype, filters in (
			("Contact", {"email_id": email}),
			("User", {"email": email}),
		):
			for name in frappe.get_all(doctype, filters=filters, pluck="name"):
				frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
	for item_code in WEB_ITEMS:
		for name in frappe.get_all("Website Item", filters={"item_code": item_code}, pluck="name"):
			frappe.delete_doc("Website Item", name, force=True, ignore_permissions=True)
	for name in frappe.get_all(
		"Item Price", filters={"item_code": "PJO2601", "price_list": PRICE_LIST}, pluck="name"
	):
		frappe.delete_doc("Item Price", name, force=True, ignore_permissions=True)
	settings = frappe.get_doc("Webshop Settings")
	settings.update({"enabled": 0, "price_list": None})
	settings.flags.ignore_permissions = True
	settings.save()
	frappe.db.commit()
	return {"frc_customers": len(frcs)}


def _guard_site() -> None:
	if frappe.local.site != SITE:
		raise RuntimeError(f"Refusing to change Webshop on {frappe.local.site}; expected {SITE}.")


def _frc_customers() -> list[dict]:
	rows = frappe.get_all(
		"Customer",
		filters={"customer_group": FRC_GROUP},
		fields=["name", "customer_name"],
		limit=100,
	)
	return [row for row in rows if row["customer_name"].endswith("(FRC)")]


def _email(customer_name: str) -> str:
	digits = re.sub(r"\D", "", customer_name)
	return f"frc{digits}@erp.local"


def _first_name(customer_name: str) -> str:
	return customer_name.replace("(FRC)", "").strip()[:40] or "FRC"


def _ensure_user(email: str, first_name: str, password: str) -> None:
	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first_name,
				"user_type": "Website User",
				"send_welcome_email": 0,
				"new_password": password,
			}
		)
		user.insert(ignore_permissions=True)
	else:
		user = frappe.get_doc("User", email)
		user.new_password = password
		user.flags.ignore_permissions = True
		user.save()
	# Website User login memakai get_route(User.default_app) sebagai home_page.
	# warehouse_app -> /all-products (entri pertama add_to_apps_screen), sehingga
	# FRC tidak dilempar ke /apps -> /desk (403).
	if frappe.db.get_value("User", email, "default_app") != "warehouse_app":
		frappe.db.set_value("User", email, "default_app", "warehouse_app")
	add_role(email, "Customer")


def _ensure_contact(email: str, first_name: str, customer_name: str) -> None:
	existing = frappe.get_all(
		"Contact",
		filters={"email_id": email},
		fields=["name"],
		limit=5,
	)
	if existing:
		contact = frappe.get_doc("Contact", existing[0]["name"])
		if not any(link.link_name == customer_name for link in contact.links):
			contact.append("links", {"link_doctype": "Customer", "link_name": customer_name})
			contact.flags.ignore_permissions = True
			contact.save()
		return
	contact = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": first_name,
			"email_ids": [{"email_id": email, "is_primary": 1}],
			"links": [{"link_doctype": "Customer", "link_name": customer_name}],
		}
	)
	contact.insert(ignore_permissions=True, ignore_mandatory=True)


def _ensure_portal_user(customer_name: str, email: str) -> None:
	if frappe.db.exists("Portal User", {"parent": customer_name, "user": email}):
		return
	customer = frappe.get_doc("Customer", customer_name)
	customer.append("portal_users", {"user": email})
	customer.flags.ignore_permissions = True
	customer.flags.ignore_mandatory = True
	customer.save()


def _ensure_portal_user_removed(customer_name: str, email: str) -> None:
	for name in frappe.get_all(
		"Portal User", filters={"parent": customer_name, "user": email}, pluck="name"
	):
		frappe.delete_doc("Portal User", name, force=True, ignore_permissions=True)


def _publish_items() -> None:
	for item_code, warehouse in WEB_ITEMS.items():
		item_name = frappe.db.get_value("Item", item_code, "item_name")
		existing = frappe.get_all(
			"Website Item", filters={"item_code": item_code}, fields=["name"], limit=1
		)
		if existing:
			doc = frappe.get_doc("Website Item", existing[0]["name"])
			doc.update({"published": 1, "website_warehouse": warehouse})
			doc.flags.ignore_permissions = True
			doc.save()
			continue
		frappe.get_doc(
			{
				"doctype": "Website Item",
				"web_item_name": item_name,
				"item_code": item_code,
				"website_warehouse": warehouse,
				"published": 1,
			}
		).insert(ignore_permissions=True)


def _ensure_dry_price() -> None:
	if frappe.db.exists("Item Price", {"item_code": "PJO2601", "price_list": PRICE_LIST}):
		return
	frappe.get_doc(
		{
			"doctype": "Item Price",
			"item_code": "PJO2601",
			"price_list": PRICE_LIST,
			"price_list_rate": DRY_PRICE,
		}
	).insert(ignore_permissions=True)
