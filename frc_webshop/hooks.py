app_name = "frc_webshop"
app_title = "FRC Webshop"
app_publisher = "Muhammad Yusuf Tri Daryanto"
app_description = "Custom FRC storefront UI on ERPNext Webshop"
app_email = "ropierpnext@gmail.com"
app_license = "mit"

required_apps = ["erpnext"]

before_request = ["frc_webshop.webshop_shell.allow_admin_invoice_detail"]

web_include_css = "/assets/frc_webshop/css/frc-webshop.css?v=45"
web_include_js = "/assets/frc_webshop/js/frc-webshop.js?v=45"

update_website_context = [
	"frc_webshop.webshop_shell.enable_portal_sidebar",
	"frc_webshop.webshop_shell.close_orders_route",
]

page_renderer = [
	"frc_webshop.webshop_shell.OrdersAccessRedirect",
	"frc_webshop.webshop_shell.StorefrontLoginRedirect",
	"frc_webshop.webshop_shell.InvoiceAccessRedirect",
]
