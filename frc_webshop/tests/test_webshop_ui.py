import frappe
from frappe.tests import IntegrationTestCase

ENDPOINT = "frc_webshop.webshop_ui.get_webshop_item_uoms"


class TestWebshopUI(IntegrationTestCase):
    def test_quotation_items_include_name_and_uom_for_portal_user(self):
        frappe.set_user("frc260158@erp.local")
        try:
            result = frappe.call(
                ENDPOINT,
                doctype="Quotation",
                name="QTN-CART-00001",
            )
        finally:
            frappe.set_user("Administrator")

        self.assertEqual(
            [row["item_code"] for row in result["items"]],
            ["PJO2601", "PJ260010"],
        )
        self.assertEqual(result["items"][0]["item_name"], "Ropi Coklat Matang")
        self.assertEqual(result["items"][1]["uom"], "Pack")
        for row in result["items"]:
            for field in ("qty", "rate", "amount"):
                self.assertIn(field, row)
                self.assertTrue(row[field], field)

    def test_endpoint_returns_quotation_meta_for_portal_user(self):
        frappe.set_user("frc260158@erp.local")
        try:
            result = frappe.call(
                ENDPOINT,
                doctype="Quotation",
                name="QTN-CART-00001",
            )
        finally:
            frappe.set_user("Administrator")

        self.assertEqual(
            result["meta"],
            {
                "owner": "Administrator",
                "customer_name": "Harapan indah (FRC)",
                "status": "Ordered",
                "docstatus": 1,
                "transaction_date": result["meta"]["transaction_date"],
                "creation": result["meta"]["creation"],
                "modified": result["meta"]["modified"],
                "grand_total": result["meta"]["grand_total"],
            },
        )
        for field in ("transaction_date", "creation", "modified", "grand_total"):
            self.assertTrue(result["meta"][field], field)

    def test_endpoint_meta_does_not_leak_other_users_quotation(self):
        frappe.set_user("frc260158@erp.local")
        try:
            with self.assertRaises(frappe.PermissionError):
                frappe.call(
                    ENDPOINT,
                    doctype="Quotation",
                    name="SAL-QTN-2026-00001",
                )
        finally:
            frappe.set_user("Administrator")

    def test_endpoint_allows_browser_post_call(self):
        # frappe.call from JS posts by default; a GET-only whitelist rejects it.
        method = frappe.get_attr(ENDPOINT)
        self.assertIn("POST", frappe.allowed_http_methods_for_whitelisted_func[method])

    def test_rejects_non_quotation_doctype(self):
        with self.assertRaises(frappe.PermissionError):
            frappe.call(
                ENDPOINT,
                doctype="Sales Order",
                name="SORD-JURI-261123001",
            )

    def test_marketplace_shell_assets_present(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()

        self.assertIn(".frc-store-bar", css)
        self.assertIn(".frc-summary", css)
        self.assertIn("get_cart_quotation", js)
        self.assertIn("data-frc-decorated", js)
        self.assertIn("parentNode.insertBefore", js)
        self.assertIn('td:first-child .notes', js)
        self.assertIn("grid-template-columns: minmax(0, 1fr) 360px", css)
        self.assertIn("width: 100% !important;\n\tmax-width: none !important;", css)
        self.assertIn("tr.frc-notes-collapsed .notes", css)
        self.assertIn("frc-note-toggle", js)
        self.assertIn(
            'body[data-path="all-products"] .page_content > .row:has(.filters-section > .title-section:only-child)',
            css,
        )
        self.assertIn("grid-template-columns: repeat(4, minmax(0, 1fr))", css)
        self.assertIn('localStorage.setItem("product_view", "Grid View")', js)
        self.assertIn('[data-section="shipping-address"],', css)
        self.assertNotIn("addAddressHint", js)

    def test_storefront_assets_are_cache_busted(self):
        # Plain asset paths get no hash from bundled_asset(); browsers pin the old JS forever.
        def hook_text(hook):
            value = frappe.get_hooks(hook) or ""
            return " ".join(value) if isinstance(value, (list, tuple)) else value

        self.assertIn("?v=", hook_text("web_include_js"))
        self.assertIn("?v=", hook_text("web_include_css"))

    def test_cart_totals_refresh_after_native_cart_update(self):
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()

        self.assertIn("new MutationObserver(refresh)", js)
        self.assertIn("items = (r.message && r.message.doc && r.message.doc.items) || []", js)

    def test_all_products_uses_sales_uom_price(self):
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()

        self.assertIn(
            "webshop.webshop.shopping_cart.product_info.get_product_info_for_website", js
        )
        self.assertIn("formatted_price_sales_uom", js)
        self.assertIn(
            "#products-grid-area .item-card, #products-list-area .list-row", js
        )

    def test_storefront_items_are_published(self):
        from frc_webshop.setup.publish_storefront_items import (
            get_storefront_items,
            publish_storefront_items,
        )

        publish_storefront_items()
        self.assertEqual(
            frappe.db.get_single_value("Webshop Settings", "products_per_page"), 48
        )
        items = get_storefront_items()
        self.assertEqual(len(items), 41)
        for item in items:
            website_item = frappe.db.get_value(
                "Website Item",
                {"item_code": item["name"]},
                ["name", "published", "website_image"],
            )
            self.assertTrue(website_item, item["name"])
            self.assertEqual(website_item[1], 1, item["name"])
            self.assertEqual(
                website_item[2],
                f"/assets/frc_webshop/images/products/{item['name']}.png",
                item["name"],
            )

        pos_codes = frappe.get_all(
            "Item", filters={"item_group": "Produk Jadi Outlet"}, pluck="name"
        )
        for item_code in pos_codes:
            website_item = frappe.db.get_value(
                "Website Item", {"item_code": item_code}, ["name", "published"]
            )
            if website_item:
                self.assertEqual(website_item[1], 0, item_code)

    def test_quotation_page_has_marketplace_cards(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()

        self.assertIn(".frc-product-line", css)
        self.assertIn(".frc-payment-total", css)
        self.assertIn("frc-order-detail", js)
        self.assertIn("money(meta && meta.grand_total)", js)
        self.assertIn(".frc-detail-header", css)
        self.assertIn("body:has(.sidebar-column) .main-column > .page-content-wrapper", css)

    def test_quotation_list_renders_pipeline_status(self):
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        self.assertIn('data-doctype="Quotation"', js)
        self.assertIn("frappe.client.get_list", js)
        self.assertIn('["Sales Order Item", "prevdoc_docname"', js)
        self.assertIn('["Delivery Note Item", "against_sales_order"', js)
        self.assertIn('["Sales Invoice Item", "sales_order"', js)
        self.assertIn(
            'const STAGE_LABELS = ["Quotation", "Sales Order", "Invoice", "Delivery"];',
            js,
        )
        self.assertLess(
            js.index('fetchRows("Sales Invoice", [["Sales Invoice Item"'),
            js.index('fetchRows("Delivery Note", [["Delivery Note Item"'),
        )
        self.assertIn("frc-pipeline", js)
        self.assertIn(".web-list-item", css)
        self.assertIn(".frc-pipeline", css)

    def test_quotation_list_shows_custom_row_instead_of_native_stack(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        anchor = css.split(".website-list.frc-quote-list .web-list-item > a {", 1)[1].split("}", 1)[0]
        for expected in (
            "position: static",
            "width: auto",
            "height: auto",
            "opacity: 1",
            "overflow: visible",
            "text-indent: 0",
        ):
            self.assertIn(expected, anchor)

        self.assertIn(
            ".website-list.frc-quote-list .web-list-item > .row {\n\tdisplay: none;\n}",
            css,
        )
        card = css.split(".website-list.frc-quote-list .web-list-item {", 1)[1].split("}", 1)[0]
        self.assertIn("padding: 0;", card)

        self.assertIn('grid-template-areas: "main status" "pipeline pipeline";', css)
        self.assertIn('grid-template-areas: "main status";', css)
        self.assertIn("justify-self: end;", css)

    def test_invoice_list_uses_the_same_compact_row(self):
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        self.assertIn("function initInvoiceList()", js)
        self.assertIn('data-doctype="Sales Invoice"', js)
        self.assertIn("initInvoiceList();", js)
        self.assertIn('dateField: "posting_date"', js)
        self.assertIn("withPipeline: false", js)
        self.assertIn(".frc-quote-row.frc-no-pipeline", css)

    def test_mobile_quotation_and_invoice_lists_clear_the_bottom_nav(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        self.assertIn(
            'body[data-path="quotations"] .row:has(.sidebar-column) > .main-column,',
            css,
        )
        self.assertIn(
            'body[data-path="invoices"] .row:has(.sidebar-column) > .main-column {',
            css,
        )
        self.assertIn(
            "padding-bottom: calc(88px + env(safe-area-inset-bottom, 0px)) !important;",
            css,
        )

    def test_mobile_transaction_list_uses_full_content_width(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        self.assertIn("body:has(.website-list.frc-quote-list) main.container {", css)
        self.assertIn("padding-left: 0 !important;", css)
        self.assertIn("padding-right: 0 !important;", css)
        self.assertIn("body:has(.website-list.frc-quote-list) .website-list {", css)
        self.assertIn("margin-left: 0 !important;", css)
        self.assertIn("width: 100% !important;", css)

    def test_quotation_summary_uses_formatted_values_from_endpoint(self):
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()

        self.assertIn("meta.grand_total", js)
        self.assertIn("row.amount", js)
        self.assertNotIn("nativeGrandTotal", js)

    def test_shell_is_scoped_and_responsive(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()

        # Navbar trimming now applies to every page once the storefront shell has a sidebar.
        self.assertIn("body:has(.sidebar-column) .navbar .navbar-brand,", css)
        self.assertIn("body:has(.sidebar-column) .navbar .navbar-toggler {", css)
        self.assertIn("body:has(.sidebar-column) .navbar .navbar-collapse {", css)
        self.assertIn(".frc-nav-toggle {", css)
        self.assertIn("body.frc-sidebar-collapsed", css)
        self.assertIn("body.frc-sidebar-open", css)
        self.assertIn(".web-sidebar .title:empty::before {", css)
        self.assertIn(r'content: "FRC"', css)
        self.assertIn('a[href="/all-products"]::before', css)
        self.assertIn("grid-template-columns: minmax(0, 1fr) 360px !important;", css)

        self.assertIn("function addProductsLink()", js)
        self.assertIn('addSidebarLink("/all-products", "All Products")', js)
        self.assertIn("function initShellToggle()", js)
        self.assertIn('className = "frc-nav-toggle"', js)
        self.assertIn("frc-sidebar-collapsed", js)
        self.assertIn("frc-sidebar-open", js)
    def test_mobile_navbar_stays_one_line(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        blocks = css.split("@media (max-width: 991px) {")[1:]
        navbar = next((b for b in blocks if "navbar-collapse" in b), "")
        self.assertIn("body:has(.sidebar-column) .navbar .navbar-collapse", navbar)
        self.assertIn("flex-direction: row", navbar)
        self.assertIn("align-items: center", navbar)
        self.assertIn("max-height: none", navbar)
        self.assertIn(".navbar-collapse .d-block.d-lg-none", navbar)
        self.assertIn("display: none", navbar)
        self.assertIn("top: 50%", css)

    def test_mobile_sidebar_becomes_bottom_nav(self):
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        self.assertIn("function addBottomNav(", js)
        self.assertIn('frc-bottom-nav web-sidebar', js)
        self.assertIn("addBottomNav()", js)
        self.assertIn(".frc-bottom-nav {", css)
        blocks = css.split("@media (max-width: 991px) {")[1:]
        mobile = next((b for b in blocks if "frc-bottom-nav" in b), "")
        self.assertIn(".frc-bottom-nav {", mobile)
        self.assertIn("bottom: 0", mobile)
        hiding = next((b for b in blocks if ".frc-nav-toggle," in b), "")
        self.assertIn(".frc-nav-toggle,", hiding)
        self.assertIn("> .sidebar-column {", hiding)
        self.assertIn("display: none !important", hiding)
        self.assertIn(".frc-bottom-nav ul", mobile)
        self.assertIn("flex-direction: column", mobile)

    def test_bottom_nav_is_not_rendered_on_login_page(self):
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()

        nav = js.split("function addBottomNav() {", 1)[1].split("\n  }", 1)[0]
        self.assertIn('document.body.dataset.path === "login"', nav)

    def test_login_redirects_to_storefront(self):
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()

        self.assertIn("function redirectLoginToStorefront", js)
        self.assertIn('url.searchParams.set("redirect-to", "/all-products")', js)
        self.assertIn("window.history.replaceState", js)

    def test_bottom_nav_defeats_core_web_sidebar_positioning(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        blocks = css.split("@media (max-width: 991px) {")[1:]
        mobile = next((b for b in blocks if "frc-bottom-nav" in b), "")
        # Core .web-sidebar sets top:0 + height:100%, which makes our fixed nav
        # cover the whole viewport instead of sitting at the bottom.
        self.assertIn("top: auto !important", mobile)
        self.assertIn("height: auto !important", mobile)
        self.assertIn("overflow: visible !important", mobile)
        self.assertIn(".frc-bottom-nav .sidebar-item a[href=\"/me\"]", mobile)
        self.assertIn("display: flex !important", mobile)

    def test_bottom_nav_uses_visible_routes_and_unstyled_list(self):
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()

        nav = js.split("function addBottomNav() {", 1)[1].split("\n  }", 1)[0]
        self.assertIn("list.className =", nav)
        self.assertIn("list-unstyled", nav)
        self.assertIn("BOTTOM_NAV_ROUTES", js)
        routes = js.split("const BOTTOM_NAV_ROUTES = [", 1)[1].split("];", 1)[0]
        for route in ("/cart", "/all-products", "/quotations"):
            self.assertIn('"' + route + '"', routes)

    def test_mobile_product_list_view_is_a_clean_card(self):
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        routes = js.split("const BOTTOM_NAV_ROUTES = [", 1)[1].split("];", 1)[0]
        self.assertLess(
            routes.index('"/all-products"'),
            routes.index('"/cart"'),
            "Products must come before Cart in the bottom nav",
        )

        blocks = css.split("@media (max-width: 991px) {")[1:]
        mobile = next((b for b in blocks if "#products-list-area .list-row" in b), "")
        self.assertIn("border-radius: 12px", mobile)
        self.assertIn("float: none !important", mobile)
        self.assertIn("max-width: 100%", mobile)
        self.assertIn(".page_content", mobile)
        self.assertIn("padding-bottom", mobile)

    def test_desktop_sidebar_lists_products_before_cart(self):
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()

        helper = js.split("function addProductsLink() {", 1)[1].split("\n  }", 1)[0]
        # addSidebarLink uses insertBefore(firstChild), so calls render in reverse.
        # Calling Cart first produces All Products → Cart in the desktop sidebar.
        self.assertLess(
            helper.index('addSidebarLink("/cart"'),
            helper.index('addSidebarLink("/all-products"'),
            "Desktop sidebar must render All Products before Cart",
        )

    def test_mobile_cards_use_the_quote_list_horizontal_padding(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        quote = css.split(".website-list.frc-quote-list .web-list-item > a {", 1)[1].split("}", 1)[0]
        self.assertIn("padding: 16px 18px", quote)

        mobile = css.split("@media (max-width: 991px) {")[-1]
        product_row = mobile.split("#products-list-area .list-row {", 1)[1].split("}", 1)[0]
        self.assertIn("padding: 16px 18px !important", product_row)

    def test_list_view_buttons_stay_inside_compact_card(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        mobile = css.split("@media (max-width: 991px) {")[-1]
        self.assertIn("#products-list-area .cart-action-container", mobile)
        self.assertIn("margin-left: 0 !important", mobile)
        self.assertIn("#products-list-area .go-to-cart", mobile)
        self.assertIn("margin-left: 0 !important", mobile)
        self.assertIn("width: auto !important", mobile)
        self.assertIn("min-width: 0 !important", mobile)

    def test_mobile_list_children_share_one_clean_left_edge(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        mobile = css.split("@media (max-width: 991px) {")[-1]
        title = mobile.split("#products-list-area .list-row .col-8 {", 1)[1].split("}", 1)[0]
        price = mobile.split("#products-list-area .list-row .product-price {", 1)[1].split("}", 1)[0]
        action = mobile.split("#products-list-area .cart-action-container {", 1)[1].split("}", 1)[0]
        self.assertIn("width: 100% !important", title)
        self.assertIn("padding: 0 !important", title)
        self.assertNotIn("flex: 1 1 100%", title)
        self.assertIn("padding: 0 !important", price)
        self.assertIn("align-self: flex-start", action)
        self.assertIn("margin: 6px 0 0 !important", action)
        self.assertNotIn("margin: 6px 0 0 auto", action)
        self.assertIn("margin-left: 0 !important", mobile)

    def test_mobile_list_puts_price_before_quote_button(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        mobile = css.split("@media (max-width: 991px) {")[-1]
        price = mobile.split("#products-list-area .list-row .product-price {", 1)[1].split("}", 1)[0]
        action = mobile.split("#products-list-area .cart-action-container {", 1)[1].split("}", 1)[0]
        self.assertIn("order: 2", price)
        self.assertIn("order: 3", action)
        self.assertIn("display: contents", mobile)

    def test_mobile_list_looks_shopee_compact_row(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        mobile = css.split("@media (max-width: 991px) {")[-1]
        self.assertIn("#products-list-area .list-row {", mobile)
        self.assertIn("display: flex", mobile)
        self.assertIn("flex-wrap: wrap", mobile)
        self.assertIn("#products-list-area .list-image {", mobile)
        self.assertIn("flex: 0 0 88px", mobile)
        self.assertIn(".cart-indicator", mobile)
        self.assertIn("display: none !important", mobile)

    def test_mobile_list_shows_name_only_with_price_and_button_on_one_line(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        mobile = css.split("@media (max-width: 991px) {")[-1]
        self.assertIn("#products-list-area .list-row > [class*=\"col-\"] > .product-code", mobile)
        self.assertIn("display: none !important", mobile)
        self.assertIn("flex-wrap: wrap", mobile)
        self.assertIn("#products-list-area .list-row .product-price {", mobile)
        self.assertIn("font-size: 14px !important", mobile)
        self.assertIn("width: auto !important", mobile)

    def test_view_toggler_never_forces_a_hidden_area_visible(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        self.assertNotIn(
            'body[data-path="all-products"] #products-list-area {\n\t\tdisplay: block !important;',
            css,
        )
        self.assertIn(
            'body[data-path="all-products"] #products-grid-area.hidden,', css
        )
        self.assertIn(
            'body[data-path="all-products"] #products-list-area.hidden {', css
        )
        self.assertIn("display: none !important", css)
        self.assertIn(
            'body[data-path="all-products"] #products-grid-area .btn-add-to-cart-list {',
            css,
        )

    def test_storefront_pages_keep_padding_and_cart_icon(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()

        self.assertIn("body[data-path=\"cart\"] > .page-content-wrapper > main.container,", css)
        self.assertIn("body[data-path=\"all-products\"] > .page-content-wrapper > main.container {", css)
        self.assertIn("function showCartIcon()", js)
        self.assertIn('icon.classList.remove("hidden")', js)

    def test_mobile_shell_keeps_one_page_gutter(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        # Cart / All Products drop the outer gutter; the inner main.container keeps 24px.
        rule = css.split('body[data-path="cart"] > .container,', 1)[1].split("}", 1)[0]
        self.assertIn("padding-left: 0 !important", rule)
        self.assertIn("padding-right: 0 !important", rule)

        # Quotation / invoice keep the native Frappe gutter: the override must stay scoped.
        self.assertNotIn(".container:has(.sidebar-column) {\n\t\tpadding-left: 0", css)

    def test_mobile_main_column_fills_the_row(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        # Cart / All Products opt in to the full-width shell.
        rule = css.split(
            'body[data-path="cart"] .row:has(.sidebar-column) > .main-column,',
            1,
        )[1].split("}", 1)[0]
        self.assertIn("max-width: 100% !important", rule)

        # Quotation / invoice keep their original column rule (no max-width override).
        self.assertIn(
            ".row:has(.sidebar-column) > .main-column {\n"
            "\t\twidth: 100%;\n"
            "\t\tpadding-bottom: 72px !important;\n"
            "\t}",
            css,
        )

        inner = css.split(
            'body[data-path="cart"] .row:has(.sidebar-column) > .main-column .page-content-wrapper > main.container,',
            1,
        )[1].split("}", 1)[0]
        self.assertIn("max-width: none !important", inner)
        self.assertIn("margin-left: 0 !important", inner)

    def test_mobile_quote_pages_keep_their_native_gutter(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        # The single-gutter / full-width shell is cart + all-products only.
        self.assertNotIn(".container:has(.sidebar-column) {\n\t\tpadding-left: 0", css)
        self.assertNotIn(
            ".row:has(.sidebar-column) > .main-column {\n\t\twidth: 100%;\n\t\tmax-width: 100%",
            css,
        )

    def test_mobile_quotation_detail_uses_the_wide_shell(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        self.assertIn('body[data-path="order"] > .container', css)
        self.assertIn(
            'body[data-path="order"] .row:has(.sidebar-column) > .main-column',
            css,
        )
        self.assertIn(
            'body[data-path="order"] .row:has(.sidebar-column) > .main-column '
            ".page-content-wrapper > main.container",
            css,
        )
        self.assertIn(
            ".frc-detail-form.frc-order-detail {\n"
            "\t\tpadding: 0;\n"
            "\t}",
            css,
        )
        self.assertIn(
            ".frc-order-detail .frc-detail-section {\n"
            "\t\tpadding: 16px 18px;\n"
            "\t}",
            css,
        )

    def test_list_filters_use_compact_date_panel(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        self.assertIn(".website-list-filters .row > .col-6", css)
        self.assertIn(".website-list-filters .form-search", css)
        self.assertIn(".frc-date-summary", css)
        self.assertIn(".frc-date-panel", css)
        self.assertIn(".frc-date-panel-fields", css)
        self.assertIn(".frc-date-filter {\n\tposition: relative;", css)
        self.assertIn(".frc-date-panel {\n\tposition: absolute;", css)

        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()

        self.assertIn("function initListFilters()", js)
        self.assertIn("function formatDateFilterRange(", js)
        self.assertIn('Quotation: "transaction_date"', js)
        self.assertIn('"Sales Invoice": "posting_date"', js)
        self.assertIn("initListFilters();", js)
        self.assertIn('"between"', js)
        self.assertIn("frc-date-summary", js)
        self.assertIn("frc-date-panel", js)

    def test_mobile_bottom_nav_reserves_page_space(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        nav_rule = css.split(".frc-bottom-nav ul {", 1)[1].split("}", 1)[0]
        self.assertIn("margin: 0;", nav_rule)
        self.assertIn(
            "body:has(.sidebar-column)::after {\n"
            '\t\tcontent: "";\n'
            "\t\tdisplay: block;\n"
            "\t\tflex: 0 0 auto;\n"
            "\t\theight: calc(64px + env(safe-area-inset-bottom, 0px));\n"
            "\t}",
            css,
        )

    def test_webshop_caches_product_api_responses(self):
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()

        self.assertIn('"webshop.webshop.api.get_product_filter_data": CACHE_TTL', js)
        self.assertIn("[PRICE_METHOD]: CACHE_TTL", js)
        self.assertIn("sessionStorage.setItem(key", js)
        self.assertIn("function clearApiCache()", js)
        self.assertIn(
            ".btn-add-to-cart-list, .btn-add-to-cart",
            js,
        )
        self.assertIn("#page-cart .cart-container", js)

    def test_mobile_list_area_aligns_with_page_content(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        mobile = css.split("@media (max-width: 991px) {")[-1]
        rule = mobile.split("#products-list-area {", 1)[1].split("}", 1)[0]
        self.assertIn("margin-left: 0 !important", rule)
        self.assertIn("margin-right: 0 !important", rule)

    def test_mobile_cart_qty_controls_stay_on_one_row(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        # 30px minus + 46px input + 30px plus = 106px. A 92px spinner wraps
        # the plus button onto its own row.
        self.assertNotIn("tbody .number-spinner {\n\t\twidth: 92px !important;", css)
        self.assertNotIn("tbody .number-spinner .cart-qty {\n\t\twidth: 36px !important;", css)
        self.assertIn("tbody.cart-items .number-spinner {\n\twidth: 106px;\n\tmin-width: 106px;", css)

    def test_mobile_cart_hides_the_decorative_item_checkbox(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        # The disabled checkbox only repeats "all items are included"; it adds noise.
        self.assertIn(
            "#page-cart .cart-container.frc-shop .frc-item-check {\n\t\tdisplay: none !important;",
            css,
        )

    def test_mobile_cart_line_total_sits_on_the_qty_row(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        rule = css.rsplit(
            "#page-cart .cart-container.frc-shop .cart-table tbody.cart-items td:nth-child(2) {",
            1,
        )[1].split("}", 1)[0]
        self.assertIn("flex-direction: row", rule)
        self.assertIn("justify-content: space-between", rule)
        self.assertIn("width: 100% !important", rule)

        total = css.rsplit(
            "#page-cart .cart-container.frc-shop .cart-table tbody.cart-items .frc-line-total {",
            1,
        )[1].split("}", 1)[0]
        self.assertIn("margin-left: auto", total)

    def test_navbar_cart_moves_right_and_hamburger_stays_above_drawer(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        # Bootstrap's .ml-auto only pushes the cart to the right when the
        # parent .navbar-collapse is a flex container. display:block pins it
        # under the absolutely-positioned hamburger at the sidebar icon column.
        self.assertIn(
            "body:has(.sidebar-column) .navbar .navbar-collapse {\n\tdisplay: flex !important;",
            css,
        )
        self.assertIn("flex: 1 1 auto !important;", css)
        self.assertIn("position: absolute;", css)
        self.assertIn("z-index: 1060;", css)
        self.assertIn(".navbar .shopping-badge {", css)

    def test_cart_looks_shopee_and_product_grid_is_default(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()

        self.assertIn(".frc-item-check {", css)
        self.assertIn("accent-color: #ee4d2d;", css)
        self.assertIn('className = "frc-item-check"', js)
        self.assertIn('icon.style.display = ""', js)
        self.assertNotIn("frc_product_view_default", js)

    def test_storefront_pages_register_portal_sidebar_hook(self):
        self.assertIn(
            "frc_webshop.webshop_shell.enable_portal_sidebar",
            frappe.get_hooks("update_website_context"),
        )

    def test_sidebar_includes_cart_link(self):
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()

        self.assertIn('addSidebarLink("/cart", "Cart")', js)

    def test_portal_sidebar_hook_scoped_to_storefront_routes(self):
        enable_sidebar = frappe.get_attr(
            "frc_webshop.webshop_shell.enable_portal_sidebar"
        )
        original_path = getattr(frappe.local, "path", None)
        try:
            for route in ("cart", "all-products"):
                frappe.local.path = route
                self.assertEqual(enable_sidebar({}), {"show_sidebar": True})

            frappe.local.path = "quotations"
            self.assertFalse(enable_sidebar({}))
        finally:
            frappe.local.path = original_path

    def test_web_shell_matches_erpnext_desk_sidebar(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()

        self.assertIn("grid-template-columns: 260px minmax(0, 1fr)", css)
        self.assertIn(".navbar .navbar-brand,", css)
        self.assertIn(".navbar .navbar-toggler {", css)
        self.assertIn(".navbar .navbar-collapse {", css)
        self.assertIn(".web-sidebar .title::after {", css)
        self.assertIn('a[href="/purchase-orders"]', css)
        self.assertIn('a[href="/purchase-invoices"]', css)
        self.assertIn(r'content: "\f107"', css)
        self.assertIn(r'content: "\f290"', css)
        self.assertNotIn("#frc-sidebar-backdrop", css)
        self.assertNotIn("frc-sidebar-backdrop", js)
    def test_quotation_detail_is_one_clean_card(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        self.assertIn(".frc-order-detail {", css)
        self.assertIn(".frc-detail-form", css)

    def test_quotation_list_paints_pipeline_before_async_fetch(self):
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()

        immediate = js.index("paintQuoteRow(item, name, {},")
        self.assertLess(immediate, js.index('fetchRows("Quotation"'))
        self.assertIn("[true, false, false, false]", js)

    def test_collapsed_sidebar_keeps_icon_rail_visible(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        self.assertIn("body.frc-sidebar-collapsed .row:has(.sidebar-column) {", css)
        self.assertIn("grid-template-columns: 64px minmax(0, 1fr) !important;", css)
        self.assertIn("body.frc-sidebar-collapsed .web-sidebar .sidebar-item a {", css)
        self.assertNotIn("body.frc-sidebar-collapsed .web-sidebar {\n\tdisplay: none;", css)

    def test_sidebar_only_shows_storefront_destinations(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        for href in (
            "/project", "/rfq", "/supplier-quotations",
            "/shipments", "/issues", "/addresses", "/timesheets",
            "/material-requests", "/me",
        ):
            # The trailing comma marks membership in the display:none group;
            # icon rules use ::before instead.
            self.assertIn('a[href="' + href + '"],', css)
        self.assertNotIn('a[href="/invoices"],', css)
        self.assertNotIn('a[href="/orders"],', css)

    def test_quotation_detail_renders_owner_and_customer_meta(self):
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        self.assertIn("function detailField(", js)
        self.assertIn("Dibuat oleh", js)
        self.assertIn("meta.owner", js)
        self.assertIn("meta.customer_name", js)
        self.assertIn("r.message.items", js)
        self.assertIn(".frc-detail-field", css)

    def test_detail_total_uses_endpoint_meta(self):
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()

        self.assertIn("meta.grand_total", js)
        self.assertIn("row.amount", js)

    def test_orders_are_hidden_from_sidebar_and_redirected(self):
        self.assertIn(
            "frc_webshop.webshop_shell.close_orders_route",
            frappe.get_hooks("update_website_context"),
        )
        close_route = frappe.get_attr("frc_webshop.webshop_shell.close_orders_route")
        original_path = getattr(frappe.local, "path", None)
        original_redirect = getattr(frappe.flags, "redirect_location", None)
        try:
            context = {
                "sidebar_items": [
                    {"route": "/orders", "title": "Orders"},
                    {"route": "/all-products", "title": "All Products"},
                ]
            }
            frappe.local.path = "all-products"
            close_route(context)
            self.assertEqual(
                [item["route"] for item in context["sidebar_items"]],
                ["/all-products"],
            )

            for route in ("orders", "orders/SAL-ORD-00001"):
                frappe.local.path = route
                frappe.flags.redirect_location = None
                with self.assertRaises(frappe.Redirect):
                    close_route({})
                self.assertEqual(frappe.flags.redirect_location, "/all-products")

            frappe.local.path = "quotations"
            frappe.flags.redirect_location = None
            self.assertIsNone(close_route({}))
        finally:
            frappe.local.path = original_path
            frappe.flags.redirect_location = original_redirect

    def test_invoices_require_frc_customer(self):
        hook = "frc_webshop.webshop_shell.InvoiceAccessRedirect"
        self.assertIn(hook, frappe.get_hooks("page_renderer"))
        renderer = frappe.get_attr(hook)

        original_user = frappe.session.user
        original_path = getattr(frappe.local, "path", None)
        try:
            frappe.local.path = "invoices"
            frappe.set_user("frc260158@erp.local")
            self.assertFalse(renderer("Sales Invoice").can_render())

            frappe.set_user("Administrator")
            self.assertFalse(renderer("Sales Invoice").can_render())

            frappe.set_user("Guest")
            self.assertTrue(renderer("Sales Invoice").can_render())

            frappe.local.path = "quotations"
            self.assertFalse(renderer("Quotation").can_render())
        finally:
            frappe.set_user(original_user)
            frappe.local.path = original_path

    def test_storefront_catalog_requires_login(self):
        hook = "frc_webshop.webshop_shell.StorefrontLoginRedirect"
        self.assertIn(hook, frappe.get_hooks("page_renderer"))
        renderer = frappe.get_attr(hook)

        original_user = frappe.session.user
        original_path = getattr(frappe.local, "path", None)
        original_redirect = getattr(frappe.flags, "redirect_location", None)
        try:
            frappe.local.path = "all-products"
            frappe.set_user("Guest")
            self.assertTrue(renderer("all-products").can_render())
            response = renderer("all-products").render()
            self.assertEqual(response.status_code, 302)
            self.assertEqual(
                response.headers.get("Location"),
                "/login?redirect-to=/all-products",
            )

            frappe.set_user("Administrator")
            self.assertFalse(renderer("all-products").can_render())
        finally:
            frappe.set_user(original_user)
            frappe.local.path = original_path
            frappe.flags.redirect_location = original_redirect

    def test_quotation_detail_has_status_and_next_step_without_receipts(self):
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        self.assertIn("function nextStepFor(", js)
        self.assertIn("frc-next-step", js)
        self.assertIn("Langkah berikutnya", js)
        self.assertIn(".frc-next-step", css)

    def test_hamburger_aligns_with_sidebar_icon_padding(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        # Icon centers are measured inside main.container (24px padding), not the navbar:
        # expanded: 24 + 12px link margin + 16px icon inset + 10px half icon = 62px.
        # collapsed: 24 + 8px link margin + ~23px half link = 55px.
        # The toggle is 36px wide, so left must be center - 18px.
        toggle = css.split(".frc-nav-toggle {", 1)[1].split("}", 1)[0]
        collapsed = css.split("body.frc-sidebar-collapsed .frc-nav-toggle {", 1)[1].split("}", 1)[0]
        self.assertIn("left: 44px;", toggle)
        self.assertIn("body.frc-sidebar-collapsed .frc-nav-toggle", css)
        collapsed = css.split("body.frc-sidebar-collapsed .frc-nav-toggle {", 1)[1].split("}", 1)[0]
        self.assertIn("left: 38px;", collapsed)

    def test_quotation_detail_uses_marketplace_order_detail(self):
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        # Header -> customer -> products -> payment -> timestamps, all from existing data.
        self.assertIn("function buildOrderHeader(", js)
        self.assertIn("function buildCustomerSection(", js)
        self.assertIn("function buildProductSection(", js)
        self.assertIn("function buildPaymentSection(", js)
        self.assertIn("function buildTimestampSection(", js)
        self.assertIn("frc-order-detail", js)
        self.assertIn("/quotations", js)
        self.assertIn("meta.customer_name", js)
        self.assertIn("row.uom", js)
        self.assertIn("money(meta && meta.grand_total)", js)
        self.assertIn(".frc-order-detail", css)
        self.assertIn(".frc-detail-header", css)
        self.assertIn(".frc-detail-products", css)
        self.assertIn(".frc-detail-payment", css)
        self.assertIn(".frc-detail-timestamps", css)

        header = js.index("function buildOrderHeader(")
        customer = js.index("function buildCustomerSection(")
        products = js.index("function buildProductSection(")
        payment = js.index("function buildPaymentSection(")
        timestamps = js.index("function buildTimestampSection(")
        builder = js.index("function buildDetailForm(")
        self.assertLess(header, customer)
        self.assertLess(customer, products)
        self.assertLess(products, payment)
        self.assertLess(payment, timestamps)
        self.assertLess(timestamps, builder)

        form = js.split("function buildDetailForm(", 1)[1].split("// The native indicator row", 1)[0]
        self.assertLess(form.index("buildOrderHeader("), form.index("buildCustomerSection("))
        self.assertLess(form.index("buildCustomerSection("), form.index("buildProductSection("))
        self.assertLess(form.index("buildProductSection("), form.index("buildPaymentSection("))
        self.assertLess(form.index("buildPaymentSection("), form.index("buildTimestampSection("))

    def test_quotation_detail_uses_erpnext_form_layout(self):
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        self.assertIn("function detailField(", js)
        self.assertIn("meta.transaction_date", js)
        self.assertIn("meta.creation", js)
        self.assertIn("meta.modified", js)
        self.assertIn("frc-detail-form", js)
        self.assertIn("frc-order-detail", js)
        self.assertNotIn("frc-quote-banner", js)
        self.assertNotIn("Quotation berhasil dikirim", js)
        self.assertIn(".frc-order-detail", css)
        self.assertIn("body[data-path=\"order\"] .page-header-actions-block", css)
        self.assertIn("body[data-path=\"portal\"] .page-header h3 {\n\tfont-size: 26px;\n}", css)

    def test_invoice_redirect_returns_302_without_raising(self):
        renderer = frappe.get_attr("frc_webshop.webshop_shell.InvoiceAccessRedirect")
        original_user = frappe.session.user
        original_path = getattr(frappe.local, "path", None)
        original_redirect = getattr(frappe.flags, "redirect_location", None)
        try:
            frappe.local.path = "invoices"
            frappe.set_user("Guest")
            response = renderer("Sales Invoice").render()
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers.get("Location"), "/all-products")
            self.assertEqual(frappe.flags.redirect_location, "/all-products")
        finally:
            frappe.set_user(original_user)
            frappe.local.path = original_path
            frappe.flags.redirect_location = original_redirect

    def test_detail_hides_duplicate_owner_and_status_from_header(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()

        # The native indicator row puts "Submitted" by the title and repeats the
        # party name on the right; the footer already says "Dibuat oleh".
        self.assertIn('body[data-path="order"] .indicator-container .text-right', css)
        header = js.split("function buildOrderHeader(", 1)[1].split("function buildCustomerSection(", 1)[0]
        self.assertNotIn("frc-order-badge", header)

    def test_collapsed_sidebar_links_get_hover_labels(self):
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()

        ready = js.split("frappe.ready(function () {", 1)[1]
        self.assertIn("addSidebarTooltips(", ready)
        helper = js.split("function addSidebarTooltips(", 1)[1].split("\n  function ", 1)[0]
        self.assertIn('.web-sidebar .sidebar-item a', helper)
        self.assertIn('setAttribute("title"', helper)

    def test_detail_status_badge_sits_right_of_title(self):
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        helper = js.split("function placeDetailStatus(", 1)[1].split("\n  function ", 1)[0]
        self.assertIn(".page-header-wrapper", helper)
        self.assertIn(".indicator-container .indicator-pill", helper)
        self.assertIn("appendChild(pill)", helper)
        init = js.split("function initQuotation(", 1)[1].split("\n  }", 1)[0]
        self.assertIn("placeDetailStatus()", init)

        selector = 'body[data-path="order"] .page-header-wrapper .indicator-pill {'
        self.assertIn(selector, css)
        status_css = css.split(selector, 1)[1].split("}", 1)[0]
        self.assertIn("margin-left: auto;", status_css)

    def test_detail_timestamps_show_clock_only(self):
        js_path = frappe.get_app_path("frc_webshop", "public", "js", "frc-webshop.js")
        with open(js_path, encoding="utf-8") as js_file:
            js = js_file.read()

        helper = js.split("function clockTime(", 1)[1].split("\n  function ", 1)[0]
        self.assertIn(r"\d{2}:\d{2}:\d{2}", helper)
        self.assertIn("return match ? match[0]", helper)
        timestamps = js.split("function buildTimestampSection(", 1)[1].split("\n  function ", 1)[0]
        self.assertIn("clockTime(meta && meta.creation)", timestamps)
        self.assertIn("clockTime(meta && meta.modified)", timestamps)

    def test_sidebar_hides_actual_portal_routes(self):
        css_path = frappe.get_app_path("frc_webshop", "public", "css", "frc-webshop.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        for href in ("/project", "/rfq", "/material-requests"):
            self.assertIn('a[href="' + href + '"],', css)

