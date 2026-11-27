// FRC webshop: marketplace-style cart polish. Read-only — no UOM selector.
(function () {
  const UOM_CLASS = "frc-uom";
  const SHOP_CLASS = "frc-shop";
  const DECORATED = "data-frc-decorated";
  const PRICED = "data-frc-sales-priced";
  const PRICE_METHOD = "webshop.webshop.shopping_cart.product_info.get_product_info_for_website";

  // Cache the two product APIs for a minute so returning to All Products paints instantly.
  const CACHE_VERSION =
    (document.currentScript && (document.currentScript.src.match(/[?&]v=(\d+)/) || [])[1]) || "0";
  const CACHE_PREFIX = "frc-api:" + CACHE_VERSION + ":";
  const CACHE_TTL = 60000;
  const CACHE_METHODS = {
    "webshop.webshop.api.get_product_filter_data": CACHE_TTL,
    [PRICE_METHOD]: CACHE_TTL,
  };

  function apiCacheKey(method, args) {
    const user = (window.frappe && frappe.session && frappe.session.user) || "Guest";
    return CACHE_PREFIX + user + ":" + method + ":" + JSON.stringify(args || {});
  }

  function readApiCache(key) {
    try {
      const hit = JSON.parse(sessionStorage.getItem(key) || "null");
      return hit && Date.now() - hit.at < hit.ttl ? hit.message : null;
    } catch (e) {
      return null;
    }
  }

  function writeApiCache(key, message, ttl) {
    try {
      sessionStorage.setItem(key, JSON.stringify({ at: Date.now(), ttl: ttl, message: message }));
    } catch (e) {
      // Private mode or storage quota: caching is optional.
    }
  }

  function clearApiCache() {
    try {
      Object.keys(sessionStorage).forEach(function (key) {
        if (key.indexOf(CACHE_PREFIX) === 0) sessionStorage.removeItem(key);
      });
    } catch (e) {
      // Nothing to clear.
    }
  }

  function installApiCache() {
    if (!window.frappe || !frappe.call || frappe.call.frcCached) return;
    const original = frappe.call;
    frappe.call = function (opts) {
      if (!opts || typeof opts !== "object" || !CACHE_METHODS[opts.method]) {
        return original.apply(this, arguments);
      }
      const key = apiCacheKey(opts.method, opts.args);
      const cached = readApiCache(key);
      if (cached !== null) {
        const response = { message: cached };
        if (typeof opts.callback === "function") {
          setTimeout(function () {
            opts.callback(response);
          }, 0);
        }
        return Promise.resolve(response);
      }
      const callback = opts.callback;
      return original.call(
        this,
        Object.assign({}, opts, {
          callback: function (r) {
            if (r && !r.exc && r.message !== undefined) {
              writeApiCache(key, r.message, CACHE_METHODS[opts.method]);
            }
            if (typeof callback === "function") callback(r);
          },
        })
      );
    };
    frappe.call.frcCached = true;
  }

  installApiCache();
  document.addEventListener(
    "click",
    function (event) {
      const target = event.target;
      const mutatesCart =
        target &&
        target.closest &&
        (target.closest(".btn-add-to-cart-list, .btn-add-to-cart") ||
          target.closest("#page-cart .cart-container"));
      if (mutatesCart) clearApiCache();
    },
    true
  );

  function money(value) {
    const amount = Number(value);
    if (!(amount > 0)) return "—";
    return new Intl.NumberFormat("id-ID", {
      style: "currency",
      currency: "IDR",
      maximumFractionDigits: 0,
    }).format(amount);
  }

  function parseMoney(text) {
    const raw = String(text || "").replace(/[^\d.,-]/g, "");
    const normalized = raw.indexOf(",") >= 0 ? raw.replace(/\./g, "").replace(",", ".") : raw;
    return Number(normalized) || 0;
  }

  function label(uom) {
    return $("<span>", { class: UOM_CLASS, text: uom });
  }

  function showCartIcon() {
    const icon = document.querySelector("li.shopping-cart.cart-icon");
    if (!icon) return;
    icon.classList.remove("hidden");
    icon.style.display = "";
  }

  function addHeadingHint() {
    const heading = document.querySelector(".shopping-cart-header");
    if (!heading || heading.nextElementSibling && heading.nextElementSibling.classList.contains("frc-heading-hint")) return;
    const hint = document.createElement("p");
    hint.className = "frc-heading-hint";
    hint.textContent = "Periksa produk, lalu ajukan quotation Anda.";
    heading.parentNode.insertBefore(hint, heading.nextSibling);
  }

  function addSidebarLink(href, text) {
    const list = document.querySelector(".web-sidebar .sidebar-items ul");
    if (!list || list.querySelector('a[href="' + href + '"]')) return;
    const item = document.createElement("li");
    item.className = "sidebar-item";
    item.innerHTML = '<a href="' + href + '">' + text + "</a>";
    list.insertBefore(item, list.firstChild);
  }

  function addProductsLink() {
    const title = document.querySelector(".web-sidebar .title");
    if (title && !title.textContent.trim()) title.textContent = "FRC";
    addSidebarLink("/cart", "Cart");
    addSidebarLink("/all-products", "All Products");
  }

  const BOTTOM_NAV_ROUTES = [
    ["/all-products", "Products"],
    ["/cart", "Cart"],
    ["/quotations", "Quotes"],
    ["/invoices", "Invoices"],
    ["/me", "Account"],
  ];

  function redirectLoginToStorefront() {
    if (document.body.dataset.path !== "login") return;
    const url = new URL(window.location.href);
    if (url.searchParams.get("redirect-to") === "/all-products") return;
    url.searchParams.set("redirect-to", "/all-products");
    window.history.replaceState(null, "", url);
  }

  function addBottomNav() {
    if (document.body.dataset.path === "login") return;
    if (document.querySelector(".frc-bottom-nav")) return;
    const list = document.createElement("ul");
    list.className = "list-unstyled";
    BOTTOM_NAV_ROUTES.forEach(function (route) {
      const item = document.createElement("li");
      item.className = "sidebar-item";
      const anchor = document.createElement("a");
      anchor.href = route[0];
      anchor.textContent = route[1];
      if (window.location.pathname.replace(/\/$/, "") === route[0]) anchor.className = "active";
      item.appendChild(anchor);
      list.appendChild(item);
    });
    const nav = document.createElement("nav");
    nav.className = "frc-bottom-nav web-sidebar";
    nav.appendChild(list);
    document.body.appendChild(nav);
  }

  function addSidebarTooltips() {
    document.querySelectorAll(".web-sidebar .sidebar-item a").forEach(function (link) {
      const label = link.textContent.trim();
      if (label) link.setAttribute("title", label);
    });
  }

  function initShellToggle() {
    const nav = document.querySelector(".navbar .container");
    if (!document.querySelector(".sidebar-column") || !nav || nav.querySelector(".frc-nav-toggle")) return;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "frc-nav-toggle";
    button.setAttribute("aria-label", "Toggle navigation");
    button.innerHTML = '<span class="frc-nav-toggle-bars"></span>';
    button.addEventListener("click", function () {
      const mobile = window.matchMedia("(max-width: 991px)").matches;
      document.body.classList.toggle(mobile ? "frc-sidebar-open" : "frc-sidebar-collapsed");
    });
    document.addEventListener("click", function (event) {
      if (!document.body.classList.contains("frc-sidebar-open")) return;
      if (event.target.closest(".sidebar-column") || event.target.closest(".frc-nav-toggle")) return;
      document.body.classList.remove("frc-sidebar-open");
    });
    nav.insertBefore(button, nav.firstChild);
  }

  function addStoreBar(container) {
    if (container.querySelector(".frc-store-bar")) return;
    const bar = document.createElement("div");
    bar.className = "frc-store-bar";
    bar.innerHTML =
      '<span class="frc-store-mark">FRC</span>' +
      '<span class="frc-store-copy"><strong>FRC Official Store</strong><span>Keranjang belanja outlet</span></span>' +
      '<span class="frc-store-count"></span>';
    container.insertBefore(bar, container.firstElementChild);
  }

  function addSummary(container) {
    if (container.querySelector(".frc-summary")) return;
    const card = document.createElement("div");
    card.className = "frc-summary";
    card.innerHTML =
      '<div class="frc-summary-head">Ringkasan Belanja</div>' +
      '<div class="frc-summary-row"><span>Total Harga <span class="frc-count"></span></span><strong class="frc-total"></strong></div>' +
      '<div class="frc-summary-note">Harga final dikonfirmasi dalam quotation.</div>';
    const panel = container.querySelector(".cart-payment-addresses");
    const paymentCard = panel && panel.querySelector(".mb-3.frappe-card");
    if (paymentCard && paymentCard.parentNode) {
      paymentCard.parentNode.insertBefore(card, paymentCard);
    } else if (panel) {
      panel.prepend(card);
    } else {
      container.appendChild(card);
    }
  }

  function addNoteToggle($row, $notes) {
    if ($row.find(".frc-note-toggle").length) return;
    const note = $notes.find("textarea").val();
    const $toggle = $("<button>", {
      type: "button",
      class: "frc-note-toggle",
      text: note ? "Ubah catatan" : "+ Tambah catatan",
    });
    $toggle.on("click", function () {
      const collapsed = $row.toggleClass("frc-notes-collapsed").hasClass("frc-notes-collapsed");
      const current = $notes.find("textarea").val();
      $toggle.text(collapsed ? (current ? "Ubah catatan" : "+ Tambah catatan") : "Sembunyikan catatan");
      if (!collapsed) $notes.find("textarea").trigger("focus");
    });
    $row.addClass("frc-notes-collapsed");
    $notes.after($toggle);
  }

  function decorateRow($row, item) {
    if ($row.attr(DECORATED)) return;
    $row.attr(DECORATED, "1");
    const uom = item.uom || "";

    // Native qty handler finds .notes inside the first cell; keep it there.
    const $notes = $row.find("td:first-child .notes");
    if ($notes.length) {
      $notes.detach().appendTo($row.find("td:first-child"));
      addNoteToggle($row, $notes);
    }

    const $firstRow = $row.find("td:first-child > .d-flex").first();
    if ($firstRow.length && !$firstRow.find(".frc-item-check").length) {
      const check = document.createElement("input");
      check.type = "checkbox";
      check.className = "frc-item-check";
      check.checked = true;
      check.disabled = true;
      check.title = "Semua item dihitung dalam quotation";
      $firstRow.prepend(check);
    }

    const $detail = $row.find("td:first-child .d-flex.w-100");
    if ($detail.length && !$detail.find(".frc-price").length) {
      const price = document.createElement("div");
      price.className = "frc-price";
      price.textContent = money(item.rate);
      if (uom) {
        const unit = document.createElement("span");
        unit.className = "frc-unit";
        unit.textContent = " / " + uom;
        price.appendChild(unit);
      }
      $detail.find(".item-subtitle").first().after(price);
    }

    const $qty = $row.find("td:nth-child(2)");
    if ($qty.length && !$qty.find(".frc-line-total").length) {
      const total = document.createElement("div");
      total.className = "frc-line-total";
      total.textContent = money(item.amount);
      $qty.append(total);
    }

    if (uom && !$row.find("." + UOM_CLASS).length) {
      $row.find(".number-spinner").after(label(uom));
    }
  }

  function paintSummary(items) {
    const container = document.querySelector(".cart-container");
    const summary = container && container.querySelector(".frc-summary");
    if (!summary) return;
    const count = items.length;
    const priced = items.some(function (item) { return Number(item.amount) > 0; });
    const total = items.reduce(function (sum, item) { return sum + (Number(item.amount) || 0); }, 0);
    summary.querySelector(".frc-count").textContent = "(" + count + " produk)";
    summary.querySelector(".frc-total").textContent = priced ? money(total) : "Dikonfirmasi";
    const badge = container.querySelector(".frc-store-count");
    if (badge) badge.textContent = count + " produk";
  }

  function detailField(labelText, value) {
    const field = document.createElement("div");
    field.className = "frc-detail-field";
    const caption = document.createElement("span");
    caption.className = "frc-field-label";
    caption.textContent = labelText;
    const content = document.createElement("span");
    content.className = "frc-field-value";
    content.textContent = value || "—";
    field.appendChild(caption);
    field.appendChild(content);
    return field;
  }

  function appendSection(form, className, title) {
    const section = document.createElement("section");
    section.className = "frc-detail-section " + className;
    if (title) {
      const heading = document.createElement("h3");
      heading.className = "frc-detail-section-title";
      heading.textContent = title;
      section.appendChild(heading);
    }
    form.appendChild(section);
    return section;
  }

  function buildOrderHeader(form, meta, name) {
    const section = appendSection(form, "frc-detail-header");
    const number = document.createElement("div");
    number.className = "frc-detail-no";
    number.textContent = name;
    section.appendChild(number);
    const date = document.createElement("div");
    date.className = "frc-detail-header-date";
    date.textContent = "Tanggal: " + ((meta && meta.transaction_date) || "—");
    section.appendChild(date);
    const back = document.createElement("a");
    back.className = "frc-detail-back";
    back.href = "/quotations";
    back.textContent = "← Kembali ke Daftar Pesanan";
    section.appendChild(back);
  }

  function buildCustomerSection(form, meta) {
    const section = appendSection(form, "frc-detail-customer", "Dipesan oleh");
    const field = detailField("Customer", meta && meta.customer_name);
    section.appendChild(field);
    const next = document.createElement("div");
    next.className = "frc-next-step";
    next.textContent = "Langkah berikutnya: " + nextStepFor(meta);
    section.appendChild(next);
  }

  function buildProductSection(form, rows) {
    const section = appendSection(form, "frc-detail-products", "Produk");
    rows.forEach(function (row) {
      const line = document.createElement("div");
      line.className = "frc-product-line";
      const info = document.createElement("div");
      const name = document.createElement("div");
      name.className = "frc-product-name";
      name.textContent = row.item_name || row.item_code || "—";
      const meta = document.createElement("div");
      meta.className = "frc-product-meta";
      meta.textContent = row.item_code || "";
      const qty = document.createElement("div");
      qty.className = "frc-product-qty";
      qty.textContent = "Qty " + (row.qty || "—") + (row.uom ? " " + row.uom : "") +
        (row.rate ? " · " + money(row.rate) + "/" + row.uom : "");
      info.appendChild(name);
      info.appendChild(meta);
      info.appendChild(qty);
      const amount = document.createElement("div");
      amount.className = "frc-product-amount";
      amount.textContent = money(row.amount);
      line.appendChild(info);
      line.appendChild(amount);
      section.appendChild(line);
    });
  }

  function paymentRow(labelText, value, total) {
    const row = document.createElement("div");
    row.className = "frc-payment-row" + (total ? " frc-payment-total" : "");
    const label = document.createElement("span");
    label.className = "frc-payment-label";
    label.textContent = labelText;
    const content = document.createElement("strong");
    content.className = "frc-payment-value";
    content.textContent = value;
    row.appendChild(label);
    row.appendChild(content);
    return row;
  }

  function buildPaymentSection(form, rows, meta) {
    const section = appendSection(form, "frc-detail-payment", "Ringkasan Pembayaran");
    const count = rows.reduce(function (sum, row) { return sum + (Number(row.qty) || 0); }, 0);
    section.appendChild(paymentRow("Total produk", count || "—", false));
    section.appendChild(paymentRow("Subtotal", money(meta && meta.grand_total), false));
    section.appendChild(paymentRow("Total pesanan", money(meta && meta.grand_total), true));
  }

  function clockTime(value) {
    const match = String(value || "").match(/\d{2}:\d{2}:\d{2}/);
    return match ? match[0] : "—";
  }

  function buildTimestampSection(form, meta) {
    const section = appendSection(form, "frc-detail-timestamps");
    [["Dibuat oleh", meta && meta.owner],
     ["Dibuat", clockTime(meta && meta.creation)],
     ["Diubah", clockTime(meta && meta.modified)]].forEach(function (field) {
      section.appendChild(detailField(field[0], field[1]));
    });
  }

  function buildDetailForm(rows, meta, name) {
    const container = document.querySelector(".order-container");
    if (!container) return;
    container.replaceChildren();
    const form = document.createElement("div");
    form.className = "frc-detail-form frc-order-detail";
    buildOrderHeader(form, meta, name);
    buildCustomerSection(form, meta);
    buildProductSection(form, rows);
    buildPaymentSection(form, rows, meta);
    buildTimestampSection(form, meta);
    container.appendChild(form);
  }

  // The native indicator row is hidden in CSS; detail content is fully rebuilt above.
  function watchCart() {
    let items = [];
    let byCode = {};
    let latest = 0;

    function paint() {
      const container = document.querySelector(".cart-container");
      if (!container) return;
      container.classList.add(SHOP_CLASS);
      addStoreBar(container);
      addSummary(container);
      $(".cart-container .cart-items tr[data-name]").each(function () {
        const $row = $(this);
        const code = $row.find(".cart-qty").attr("data-item-code");
        decorateRow($row, byCode[code] || {});
      });
      paintSummary(items);
    }

    // Native qty/remove replaces .cart-items; re-read the quotation so totals never go stale.
    function refresh() {
      const seq = ++latest;
      frappe.call({
        method: "webshop.webshop.shopping_cart.cart.get_cart_quotation",
        callback: function (r) {
          if (seq !== latest) return;
          items = (r.message && r.message.doc && r.message.doc.items) || [];
          byCode = {};
          items.forEach(function (item) {
            if (item.item_code) byCode[item.item_code] = item;
          });
          paint();
        },
      });
    }

    refresh();
    const root = document.querySelector(".cart-container .cart-items");
    if (root && window.MutationObserver) {
      new MutationObserver(refresh).observe(root, { childList: true });
    }
  }

  function initCart() {
    addHeadingHint();
    const container = document.querySelector(".cart-container");
    if (container) {
      container.classList.add(SHOP_CLASS);
      addStoreBar(container);
      addSummary(container);
    }
    watchCart();
  }

  function paintSalesUomPrice(card, info) {
    const price = card.querySelector(".product-price");
    const product = info && info.product_info;
    if (!price || !product || !product.price || !product.price.formatted_price_sales_uom) return;
    const first = price.firstChild;
    if (!first || first.nodeType !== Node.TEXT_NODE) return;
    first.textContent = product.price.formatted_price_sales_uom;
    if (product.sales_uom) {
      const unit = document.createElement("span");
      unit.className = "frc-unit";
      unit.textContent = " / " + product.sales_uom;
      price.insertBefore(unit, first.nextSibling);
    }
  }

  function alignSalesUomPrices() {
    document
      .querySelectorAll("#products-grid-area .item-card, #products-list-area .list-row")
      .forEach(function (card) {
        if (card.getAttribute(PRICED)) return;
        const button = card.querySelector("[data-item-code]");
        const itemCode = button && button.getAttribute("data-item-code");
        if (!itemCode) return;
        card.setAttribute(PRICED, "1");
        frappe.call({
          method: PRICE_METHOD,
          args: { item_code: itemCode, skip_quotation_creation: 1 },
          callback: function (r) {
            if (r.message) paintSalesUomPrice(card, r.message);
          },
        });
      });
  }

  function watchProductPrices() {
    if (!/^\/all-products\/?$/.test(window.location.pathname)) return;
    alignSalesUomPrices();
    const root = document.querySelector("#product-listing");
    if (root && window.MutationObserver) {
      new MutationObserver(alignSalesUomPrices).observe(root, { childList: true, subtree: true });
    }
  }

  // Use the native card view once; after that the user's toggle choice wins.
  function setDefaultProductView() {
    if (!/^\/all-products\/?$/.test(window.location.pathname)) return;
    localStorage.setItem("product_view", "Grid View");
  }

  const LIST_LIMIT = 20;
  const STAGE_LABELS = ["Quotation", "Sales Order", "Invoice", "Delivery"];
  const LIST_DATE_FIELDS = {
    Quotation: "transaction_date",
    "Sales Invoice": "posting_date",
  };

  function canReadPipeline() {
    return frappe.user && frappe.user.has_role("Administrator");
  }

  function fetchRows(doctype, filters, fields, limit) {
    return new Promise(function (resolve) {
      frappe.call({
        method: "frappe.client.get_list",
        args: {
          doctype: doctype,
          filters: filters,
          fields: fields,
          limit_page_length: limit === undefined ? 1 : limit,
        },
        callback: function (r) {
          resolve(Array.isArray(r.message) ? r.message : []);
        },
        error: function () {
          resolve([]);
        },
      });
    });
  }

  function quoteNameFromLink(link) {
    if (!link) return "";
    const parts = link.getAttribute("href").split("/");
    return decodeURIComponent(parts[parts.length - 1]);
  }

  function pipelineFor(name) {
    if (!canReadPipeline()) return Promise.resolve([true, false, false, false]);
    return fetchRows("Sales Order", [
      ["Sales Order Item", "prevdoc_docname", "=", name],
    ]).then(function (orders) {
      if (!orders.length) return [true, false, false, false];
      const order = orders[0].name;
      return Promise.all([
        fetchRows("Sales Invoice", [["Sales Invoice Item", "sales_order", "=", order]]),
        fetchRows("Delivery Note", [["Delivery Note Item", "against_sales_order", "=", order]]),
      ]).then(function (results) {
        return [true, true, results[0].length > 0, results[1].length > 0];
      });
    });
  }

  function stageMarkup(states) {
    return STAGE_LABELS.map(function (label, index) {
      const step = states[index] ? '<span class="frc-step done">' : '<span class="frc-step">';
      return step + label + "</span>";
    }).join('<span class="frc-step-arrow">›</span>');
  }

  function listDate(value) {
    const parts = String(value || "").split("-");
    if (parts.length !== 3) return value || "";
    const date = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    return date.toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
  }

  function paintQuoteRow(item, name, quote, states, options) {
    const link = item.querySelector("a[href]");
    if (!link) return;
    const opts = options || {};
    const withPipeline = opts.withPipeline !== false;
    const dateField = opts.dateField || "transaction_date";
    const status = quote.status || (quote.docstatus === 2 ? "Cancelled" : quote.docstatus === 1 ? "Submitted" : quote.name ? "Draft" : "Menunggu");
    link.innerHTML =
      '<div class="frc-quote-row' + (withPipeline ? "" : " frc-no-pipeline") + '">' +
        '<div class="frc-quote-main">' +
          '<div class="frc-quote-no"></div>' +
          '<div class="frc-quote-meta"></div>' +
        "</div>" +
        (withPipeline ? '<div class="frc-pipeline">' + stageMarkup(states) + "</div>" : "") +
        '<div class="frc-quote-status"></div>' +
      "</div>";
    link.querySelector(".frc-quote-no").textContent = name;
    link.querySelector(".frc-quote-meta").textContent = [
      listDate(quote[dateField]),
      quote.grand_total ? money(quote.grand_total) : "",
    ].filter(Boolean).join(" · ");
    link.querySelector(".frc-quote-status").textContent = status;
  }

  function listDateField(path) {
    if (path === "/quotations") return LIST_DATE_FIELDS.Quotation;
    if (path === "/invoices") return LIST_DATE_FIELDS["Sales Invoice"];
    return "";
  }

  function readListDateFilter(field) {
    const raw = new URLSearchParams(window.location.search).get(field);
    if (!raw) return { from: "", to: "" };
    try {
      const value = JSON.parse(raw);
      if (!Array.isArray(value)) return { from: "", to: "" };
      if (value[0] === "between" && Array.isArray(value[1])) {
        return { from: value[1][0] || "", to: value[1][1] || "" };
      }
      if (value[0] === ">=") return { from: value[1] || "", to: "" };
      if (value[0] === "<=") return { from: "", to: value[1] || "" };
    } catch (e) {
      // Ignore a malformed date filter in the URL.
    }
    return { from: "", to: "" };
  }

  function applyListDateFilter(field, from, to, searchInput) {
    let start = from;
    let end = to;
    if (start && end && start > end) {
      const swap = start;
      start = end;
      end = swap;
    }
    const params = new URLSearchParams();
    const text = searchInput ? searchInput.value.trim() : "";
    if (text) params.set("txt", text);
    if (start && end) params.set(field, JSON.stringify(["between", [start, end]]));
    else if (start) params.set(field, JSON.stringify([">=", start]));
    else if (end) params.set(field, JSON.stringify(["<=", end]));
    const query = params.toString();
    window.location.href = window.location.pathname + (query ? "?" + query : "");
  }

  function formatDateFilterRange(from, to) {
    const format = function (value, withYear) {
      const parts = String(value || "").split("-");
      if (parts.length !== 3) return value || "";
      const date = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
      const options = withYear
        ? { day: "numeric", month: "short", year: "numeric" }
        : { day: "numeric", month: "short" };
      return date.toLocaleDateString("id-ID", options);
    };
    if (from && to) {
      const sameYear = from.slice(0, 4) === to.slice(0, 4);
      return format(from, !sameYear) + " – " + format(to, true);
    }
    if (from) return "≥ " + format(from, true);
    if (to) return "≤ " + format(to, true);
    return "";
  }

  function makeListDateField(captionText, value) {
    const label = document.createElement("label");
    label.className = "frc-date-field";
    const caption = document.createElement("span");
    caption.textContent = captionText;
    const input = document.createElement("input");
    input.type = "date";
    input.className = "form-control";
    input.value = value;
    label.appendChild(caption);
    label.appendChild(input);
    return { label: label, input: input };
  }

  function initListFilters() {
    const path = window.location.pathname.replace(/\/$/, "");
    const field = listDateField(path);
    if (!field || document.querySelector(".frc-date-filter")) return;

    const list = document.querySelector(".website-list[data-doctype]");
    let filters = document.querySelector(".website-list-filters");
    const empty = document.querySelector(".page_content .empty-apps-state");
    if (!list && !filters && !empty) return;

    let row;
    let col;
    if (filters) {
      row = filters.querySelector(".row");
      col = row && row.querySelector(".col-6");
    }
    if (!filters) {
      const host = document.querySelector(".page_content") || document.querySelector("main");
      if (!host) return;
      filters = document.createElement("div");
      filters.className = "website-list-filters my-4";
      row = document.createElement("div");
      row.className = "row";
      col = document.createElement("div");
      col.className = "col-6";
      row.appendChild(col);
      filters.appendChild(row);
      host.prepend(filters);
    } else if (!row) {
      row = document.createElement("div");
      row.className = "row";
      filters.appendChild(row);
    }
    if (!col) {
      col = document.createElement("div");
      col.className = "col-6";
      row.appendChild(col);
    }

    const searchForm = filters.querySelector(".form-search");
    const searchInput = searchForm && searchForm.querySelector('input[name="txt"]');
    const initial = readListDateFilter(field);
    const from = makeListDateField("Dari", initial.from);
    const to = makeListDateField("Sampai", initial.to);

    const details = document.createElement("details");
    details.className = "frc-date-filter";
    if (initial.from || initial.to) details.classList.add("frc-has-date");

    const summary = document.createElement("summary");
    summary.className = "frc-date-summary";
    const icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    icon.setAttribute("class", "icon icon-xs");
    const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
    use.setAttribute("href", "#icon-calendar");
    icon.appendChild(use);
    const title = document.createElement("span");
    title.textContent = "Tanggal";
    const range = document.createElement("span");
    range.className = "frc-date-summary-range";
    range.textContent = formatDateFilterRange(initial.from, initial.to);
    summary.appendChild(icon);
    summary.appendChild(title);
    if (range.textContent) summary.appendChild(range);

    const panel = document.createElement("form");
    panel.className = "frc-date-panel";
    panel.method = "get";
    panel.action = path;
    const fields = document.createElement("div");
    fields.className = "frc-date-panel-fields";
    fields.appendChild(from.label);
    fields.appendChild(to.label);
    const actions = document.createElement("div");
    actions.className = "frc-date-actions";
    const apply = document.createElement("button");
    apply.type = "submit";
    apply.className = "btn btn-dark frc-date-apply";
    apply.textContent = "Terapkan";
    const reset = document.createElement("button");
    reset.type = "button";
    reset.className = "btn btn-link frc-date-reset";
    reset.textContent = "Reset";
    actions.appendChild(apply);
    actions.appendChild(reset);
    panel.appendChild(fields);
    panel.appendChild(actions);

    panel.addEventListener("submit", function (event) {
      event.preventDefault();
      applyListDateFilter(field, from.input.value, to.input.value, searchInput);
    });
    reset.addEventListener("click", function () {
      from.input.value = "";
      to.input.value = "";
      applyListDateFilter(field, "", "", searchInput);
    });
    if (searchForm) {
      searchForm.addEventListener("submit", function (event) {
        event.preventDefault();
        applyListDateFilter(field, from.input.value, to.input.value, searchInput);
      });
    }

    details.appendChild(summary);
    details.appendChild(panel);
    col.appendChild(details);
  }

  function initQuoteList() {
    if (window.location.pathname.replace(/\/$/, "") !== "/quotations") return;
    const list = document.querySelector('.website-list[data-doctype="Quotation"]');
    if (!list || list.classList.contains("frc-quote-list")) return;
    list.classList.add("frc-quote-list");
    const items = Array.from(list.querySelectorAll(".web-list-item")).slice(0, LIST_LIMIT);
    const names = items.map(function (item) {
      return quoteNameFromLink(item.querySelector("a[href]"));
    }).filter(Boolean);
    if (!names.length) return;

    // Draw the pipeline immediately; the async lookups only refine these states.
    items.forEach(function (item) {
      const name = quoteNameFromLink(item.querySelector("a[href]"));
      paintQuoteRow(item, name, {}, [true, false, false, false]);
    });

    fetchRows("Quotation", [["name", "in", names]], [
      "name", "status", "docstatus", "grand_total", "transaction_date",
    ], 0).then(function (quotes) {
      const byName = {};
      quotes.forEach(function (quote) { byName[quote.name] = quote; });
      items.forEach(function (item) {
        const name = quoteNameFromLink(item.querySelector("a[href]"));
        pipelineFor(name).then(function (states) {
          paintQuoteRow(item, name, byName[name] || {}, states);
        });
      });
    });
  }

  function initInvoiceList() {
    if (window.location.pathname.replace(/\/$/, "") !== "/invoices") return;
    const list = document.querySelector('.website-list[data-doctype="Sales Invoice"]');
    if (!list || list.classList.contains("frc-quote-list")) return;
    list.classList.add("frc-quote-list");
    const items = Array.from(list.querySelectorAll(".web-list-item")).slice(0, LIST_LIMIT);
    const names = items.map(function (item) {
      return quoteNameFromLink(item.querySelector("a[href]"));
    }).filter(Boolean);
    if (!names.length) return;

    const options = { dateField: "posting_date", withPipeline: false };
    items.forEach(function (item) {
      const name = quoteNameFromLink(item.querySelector("a[href]"));
      paintQuoteRow(item, name, {}, [], options);
    });

    fetchRows("Sales Invoice", [["name", "in", names]], [
      "name", "status", "docstatus", "grand_total", "posting_date",
    ], 0).then(function (invoices) {
      const byName = {};
      invoices.forEach(function (invoice) { byName[invoice.name] = invoice; });
      items.forEach(function (item) {
        const name = quoteNameFromLink(item.querySelector("a[href]"));
        paintQuoteRow(item, name, byName[name] || {}, [], options);
      });
    });
  }

  function nextStepFor(meta) {
    if (!meta) return "Menunggu konfirmasi FRC";
    if (meta.docstatus === 2) return "Quotation dibatalkan";
    if (meta.status === "Ordered" || meta.docstatus === 1) return "Menunggu diproses tim FRC";
    return "Menunggu konfirmasi FRC";
  }

  function placeDetailStatus() {
    const header = document.querySelector(".page-header-wrapper");
    const pill = document.querySelector(".indicator-container .indicator-pill");
    if (!header || !pill) return;
    header.appendChild(pill);
  }

  function initQuotation() {
    const match = window.location.pathname.match(/^\/quotations\/([^/]+)\/?$/);
    if (!match) return;
    placeDetailStatus();
    const container = document.querySelector(".order-container");
    if (container) container.classList.add(SHOP_CLASS);
    frappe.call({
      method: "frc_webshop.webshop_ui.get_webshop_item_uoms",
      args: { doctype: "Quotation", name: decodeURIComponent(match[1]) },
      callback: function (r) {
        if (!r.message || !Array.isArray(r.message.items)) return;
        buildDetailForm(r.message.items, r.message.meta, decodeURIComponent(match[1]));
      },
    });
  }

  setDefaultProductView();

  frappe.ready(function () {
    showCartIcon();
    addProductsLink();
    addSidebarTooltips();
    initShellToggle();
    redirectLoginToStorefront();
    addBottomNav();

    if ($(".cart-container").length) initCart();
    else if ($(".order-container").length) initQuotation();
    initListFilters();
    initQuoteList();
    initInvoiceList();
    watchProductPrices();
  });
})();
