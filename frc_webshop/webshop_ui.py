import frappe
from frappe import _

ALLOWED_DOCTYPES = {"Quotation"}


@frappe.whitelist(methods=["GET", "POST"])
def get_webshop_item_uoms(doctype: str, name: str) -> list[dict[str, str]]:
    """Return item names, purchase UOMs and header meta for a Quotation the portal user may read."""
    if doctype not in ALLOWED_DOCTYPES:
        frappe.throw(_("Not Permitted"), frappe.PermissionError)

    doc = frappe.get_doc(doctype, name)
    if not frappe.has_website_permission(doc):
        frappe.throw(_("Not Permitted"), frappe.PermissionError)

    return {
        "items": [
            {"item_code": row.item_code, "item_name": row.item_name, "uom": row.uom,
             "qty": row.qty, "rate": row.rate, "amount": row.amount}
            for row in doc.items
            if row.uom
        ],
        "meta": {
            "owner": doc.owner,
            "customer_name": doc.customer_name,
            "status": doc.status,
            "docstatus": doc.docstatus,
            "transaction_date": doc.transaction_date,
            "creation": doc.creation,
            "modified": doc.modified,
            "grand_total": doc.grand_total,
        },
    }
