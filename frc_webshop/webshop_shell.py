import frappe
from frappe.website.page_renderers.redirect_page import RedirectPage

STOREFRONT_ROUTES = {"cart", "all-products"}
REDIRECT_HOME = "/all-products"


def enable_portal_sidebar(context):
	# Frappe calls this for every website page; gate on the exact storefront route.
	if getattr(frappe.local, "path", "") in STOREFRONT_ROUTES:
		return {"show_sidebar": True}


def close_orders_route(context):
	"""Hide Orders from the portal sidebar and block its URL for everyone."""
	items = context.get("sidebar_items")
	if items:
		context["sidebar_items"] = [
			item for item in items if item.get("route", "").rstrip("/") != "/orders"
		]

	path = (getattr(frappe.local, "path", "") or "").strip("/")
	if path == "orders" or path.startswith("orders/"):
		frappe.flags.redirect_location = REDIRECT_HOME
		raise frappe.Redirect


class InvoiceAccessRedirect(RedirectPage):
	"""Send non-FRC visitors away from /invoices before the page renders."""

	def __init__(self, path=None, http_status_code=None):
		path = (getattr(frappe.local, "path", "") or path or "").strip("/")
		super().__init__(path, 302)
		self.blocked = path == "invoices" or path.startswith("invoices/")

	def can_render(self):
		return self.blocked and not self.has_access()

	def has_access(self):
		user = frappe.session.user
		if user == "Administrator" or "System Manager" in frappe.get_roles():
			return True
		if user == "Guest":
			return False

		from erpnext.controllers.website_list_for_contact import get_customers_suppliers

		customers = get_customers_suppliers("Sales Invoice", user)[0] or []
		return bool(
			customers
			and frappe.db.exists(
				"Customer", {"name": ["in", customers], "customer_name": ["like", "%(FRC)%"]}
			)
		)

	def render(self):
		frappe.flags.redirect_location = REDIRECT_HOME
		return super().render()
