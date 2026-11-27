"""Publish factory finished goods and outlet dry goods to the FRC webshop."""

import os

import frappe

APP_NAME = "frc_webshop"
FACTORY_GROUP = "Produk Jadi Pabrik"
DRY_GROUP = "Bahan Baku"
DEFAULT_WAREHOUSE = "Gudang Barang Jadi - JURI"
FACTORY_WAREHOUSES = ("Gudang Barang Jadi - JURI", "Gudang Jakarta - JURI")
PRODUCTION_WAREHOUSES = (
	"Gudang Produksi - JURI",
	"Work In Progress - JURI",
	"Gudang R&D - JURI",
)
SKIP_NAMES = {"Botol (250 ml)"}


def _warehouses_by_item(item_codes: list[str]) -> dict[str, set[str]]:
	bins = frappe.get_all(
		"Bin",
		filters={"item_code": ["in", item_codes], "actual_qty": [">", 0]},
		fields=["item_code", "warehouse"],
		limit_page_length=0,
	)
	warehouses = {}
	for row in bins:
		warehouses.setdefault(row.item_code, set()).add(row.warehouse)
	return warehouses


def get_storefront_items() -> list[dict]:
	items = [
		{
			"name": row.name,
			"item_name": (row.item_name or row.name).strip(),
			"warehouse": DEFAULT_WAREHOUSE,
		}
		for row in frappe.get_all(
			"Item",
			filters={"item_group": FACTORY_GROUP, "disabled": 0},
			fields=["name", "item_name"],
			order_by="name asc",
			limit_page_length=0,
		)
	]

	dry_items = frappe.get_all(
		"Item",
		filters={"item_group": DRY_GROUP, "disabled": 0},
		fields=["name", "item_name"],
		order_by="name asc",
		limit_page_length=0,
	)
	warehouses = _warehouses_by_item([row.name for row in dry_items])
	for row in dry_items:
		item_name = (row.item_name or row.name).strip()
		if item_name in SKIP_NAMES:
			continue
		item_warehouses = warehouses.get(row.name, set())
		if not any(w in FACTORY_WAREHOUSES for w in item_warehouses):
			continue
		if any(w in PRODUCTION_WAREHOUSES for w in item_warehouses):
			continue
		items.append(
			{
				"name": row.name,
				"item_name": item_name,
				"warehouse": next(
					w for w in FACTORY_WAREHOUSES if w in item_warehouses
				),
			}
		)

	return items


def _image_url(item_code: str) -> str | None:
	path = frappe.get_app_path(
		APP_NAME, "public", "images", "products", f"{item_code}.png"
	)
	if os.path.exists(path):
		return f"/assets/{APP_NAME}/images/products/{item_code}.png"
	return None


def _save_website_item(doc) -> None:
	previous = frappe.flags.in_import
	frappe.flags.in_import = True
	try:
		if doc.is_new():
			doc.insert()
		else:
			doc.save()
	finally:
		frappe.flags.in_import = previous


def _is_pos_item(item_code: str, pos_groups: set[str]) -> bool:
	group = frappe.db.get_value("Item", item_code, "item_group")
	while group:
		if group in pos_groups:
			return True
		group = frappe.db.get_value("Item Group", group, "parent_item_group")
	return False


def unpublish_pos_items(exclude_codes: set[str] | None = None) -> int:
	exclude_codes = exclude_codes or set()
	pos_groups = {
		row.item_group
		for row in frappe.get_all(
			"POS Item Group",
			fields=["item_group"],
			limit_page_length=0,
		)
	}
	unpublished = 0
	for row in frappe.get_all(
		"Website Item",
		filters={"published": 1},
		fields=["name", "item_code"],
		limit_page_length=0,
	):
		if row.item_code in exclude_codes:
			continue
		item_name = frappe.db.get_value("Item", row.item_code, "item_name") or ""
		if "matang" in item_name.lower() or _is_pos_item(
			row.item_code, pos_groups
		):
			doc = frappe.get_doc("Website Item", row.name)
			doc.published = 0
			doc.flags.ignore_permissions = True
			doc.save()
			unpublished += 1
	return unpublished


def publish_storefront_items() -> int:
	items = get_storefront_items()
	unpublish_pos_items({item["name"] for item in items})
	published = 0
	for item in items:
		website_item = frappe.db.get_value(
			"Website Item", {"item_code": item["name"]}, "name"
		)
		doc = (
			frappe.get_doc("Website Item", website_item)
			if website_item
			else frappe.new_doc("Website Item")
		)
		if doc.is_new():
			doc.item_code = item["name"]
			doc.web_item_name = item["item_name"]

		doc.published = 1
		if item["warehouse"] and frappe.db.exists("Warehouse", item["warehouse"]):
			doc.website_warehouse = item["warehouse"]

		image = _image_url(item["name"])
		if image:
			doc.website_image = image
			doc.thumbnail = None

		doc.flags.ignore_permissions = True
		_save_website_item(doc)
		published += 1

	return published
