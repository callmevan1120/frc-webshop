import frappe
from erpnext.controllers.website_list_for_contact import (
	has_website_permission as erpnext_website_permission,
)
from erpnext.selling.doctype.sales_order.sales_order import SalesOrder

from frc_webshop.webshop_shell import is_frc_admin


class FRCSalesOrder(SalesOrder):
	def has_website_permission(self, ptype="read", user=None, verbose=False):
		"""Let FRC admins use normal Sales Order read permission on the portal."""
		if is_frc_admin(user):
			return self.has_permission(ptype, user=user)
		return erpnext_website_permission(self, ptype, user or frappe.session.user, verbose)
