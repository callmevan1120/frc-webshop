"""Cuplikan hook FRC Webshop.

Gabungkan ke hooks.py app Frappe tempat file-file frc_webshop disalin.
Cache-buster wajib di-bump setiap kali CSS/JS diubah.
"""

# include js, css files in header of web template
web_include_css = "/assets/<app>/css/frc-webshop.css?v=23"
web_include_js = "/assets/<app>/js/frc-webshop.js?v=23"

# FRC storefront uses the same portal shell as the quotation pages.
update_website_context = [
	"frc_webshop.webshop_shell.enable_portal_sidebar",
	"frc_webshop.webshop_shell.close_orders_route",
]

# Answer /invoices with a redirect before any page renders.
page_renderer = [
	"frc_webshop.webshop_shell.InvoiceAccessRedirect",
]
