"""Publish factory finished goods to the FRC webshop."""

import os

import frappe

ITEM_GROUP = "Produk Jadi Pabrik"
WAREHOUSE = "Gudang Barang Jadi - JURI"

PHOTOS = {
	"PJ260010": "/files/CROISSANT ORIGINAL.png",
	"PJ260011": "/files/GEMPI ORIGINAL.png",
	"PJ260012": "/files/ROPI BUTTER.png",
	"PJ260013": "/files/ROPI COKLAT.png",
	"PJ260014": "/files/ROPI KEJU.png",
	"PJ260009": "/files/AIR MINERAL CRYSTALIN.jpg",
	"Dough Croissant": "/files/CROISSANT ORIGINAL.png",
	"Dough Gempi": "/files/GEMPI ORIGINAL.png",
	"Dough Ropi Butter": "/files/ROPI BUTTER.png",
	"Dough Ropi Coklat": "/files/ROPI COKLAT.png",
	"Dough Ropi Keju": "/files/ROPI KEJU.png",
	"Air Mineral Outlet (600 ml)": "/files/AIR MINERAL CRYSTALIN.jpg",
}


def publish_factory_items() -> int:
	if not frappe.db.exists("Item Group", ITEM_GROUP):
		return 0

	warehouse_exists = frappe.db.exists("Warehouse", WAREHOUSE)
	items = frappe.get_all(
		"Item",
		filters={"item_group": ITEM_GROUP, "disabled": 0},
		fields=["name", "item_name"],
		order_by="name asc",
		limit_page_length=0,
	)

	published = 0
	for item in items:
		website_item = frappe.db.get_value("Website Item", {"item_code": item.name}, "name")
		doc = frappe.get_doc("Website Item", website_item) if website_item else frappe.new_doc("Website Item")
		if doc.is_new():
			doc.item_code = item.name
			doc.web_item_name = (item.item_name or item.name).strip()

		doc.published = 1
		if warehouse_exists and not doc.website_warehouse:
			doc.website_warehouse = WAREHOUSE

		photo = PHOTOS.get(item.name) or PHOTOS.get((item.item_name or "").strip())
		if photo and not doc.website_image and os.path.exists(
			frappe.get_site_path("public", photo.lstrip("/"))
		):
			doc.website_image = photo

		doc.flags.ignore_permissions = True
		if doc.is_new():
			doc.insert()
		else:
			doc.save()
		published += 1

	return published
