import frappe
from frappe import _

ALLOWED_DOCTYPES = {"Quotation", "Sales Invoice"}


@frappe.whitelist(methods=["GET", "POST"])
def get_webshop_item_uoms(doctype: str, name: str) -> dict:
    """Return item rows and header meta for a portal Quotation or Sales Invoice."""
    if doctype not in ALLOWED_DOCTYPES:
        frappe.throw(_("Not Permitted"), frappe.PermissionError)

    doc = frappe.get_doc(doctype, name)
    if not frappe.has_website_permission(doc):
        frappe.throw(_("Not Permitted"), frappe.PermissionError)

    meta = {
        "owner": doc.owner,
        "customer_name": doc.customer_name,
        "status": doc.status,
        "docstatus": doc.docstatus,
        "transaction_date": doc.get("transaction_date"),
        "creation": doc.creation,
        "modified": doc.modified,
        "grand_total": doc.grand_total,
    }
    if doctype == "Sales Invoice":
        meta.update({
            "posting_date": doc.posting_date,
            "due_date": doc.due_date,
            "outstanding_amount": doc.outstanding_amount,
        })

    return {
        "items": [
            {"item_code": row.item_code, "item_name": row.item_name, "uom": row.uom,
             "qty": row.qty, "rate": row.rate, "amount": row.amount}
            for row in doc.items
            if row.uom
        ],
        "meta": meta,
    }
