import frappe
from frappe.website.page_renderers.redirect_page import RedirectPage

STOREFRONT_ROUTES = {"cart", "all-products"}
REDIRECT_HOME = "/all-products"


def is_frc_admin(user=None):
	user = user or frappe.session.user
	return user == "Administrator" or "System Manager" in frappe.get_roles(user)


def allow_admin_invoice_detail():
	"""Webshop's order page only checks customer links; admins use role permission."""
	from erpnext.controllers import website_list_for_contact

	current = website_list_for_contact.has_website_permission
	if getattr(current, "_frc_admin_invoice", False):
		return

	def has_website_permission(doc, ptype, user, verbose=False):
		if (
			doc is not None
			and getattr(doc, "doctype", None) == "Sales Invoice"
			and is_frc_admin(user)
		):
			return doc.has_permission(ptype, user=user)
		return current(doc, ptype, user, verbose)

	has_website_permission._frc_admin_invoice = True
	website_list_for_contact.has_website_permission = has_website_permission


def enable_portal_sidebar(context):
	# Frappe calls this for every website page; gate on the exact storefront route.
	if getattr(frappe.local, "path", "") in STOREFRONT_ROUTES:
		return {"show_sidebar": True}


def close_orders_route(context):
	"""Hide Orders from the portal sidebar; the route renderer blocks its URL."""
	items = context.get("sidebar_items")
	if items:
		context["sidebar_items"] = [
			item for item in items if item.get("route", "").rstrip("/") != "/orders"
		]


class StorefrontLoginRedirect(RedirectPage):
	"""Require login before showing the storefront catalog."""

	def __init__(self, path=None, http_status_code=None):
		path = (getattr(frappe.local, "path", "") or path or "").strip("/")
		super().__init__(path, 302)
		self.blocked = path == "all-products"

	def can_render(self):
		return self.blocked and frappe.session.user == "Guest"

	def render(self):
		frappe.flags.redirect_location = "/login?redirect-to=/all-products"
		return super().render()


class OrdersAccessRedirect(RedirectPage):
	"""Hide the Orders route for everyone."""

	def __init__(self, path=None, http_status_code=None):
		path = (getattr(frappe.local, "path", "") or path or "").strip("/")
		super().__init__(path, 302)
		self.blocked = path == "orders" or path.startswith("orders/")

	def can_render(self):
		return self.blocked

	def render(self):
		frappe.flags.redirect_location = REDIRECT_HOME
		return super().render()


class InvoiceAccessRedirect(RedirectPage):
	"""Send non-FRC visitors away from /invoices before the page renders."""

	def __init__(self, path=None, http_status_code=None):
		path = (getattr(frappe.local, "path", "") or path or "").strip("/")
		super().__init__(path, 302)
		self.blocked = path == "invoices" or path.startswith("invoices/")

	def can_render(self):
		return self.blocked and not self.has_access()

	def has_access(self):
		if is_frc_admin():
			return True

		user = frappe.session.user
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
