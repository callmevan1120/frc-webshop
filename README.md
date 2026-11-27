# FRC Webshop — custom storefront for Frappe/ERPNext

Kustomisasi **storefront FRC** di atas Webshop ERPNext: satu shell portal yang rapi,
halaman detail Quotation bergaya marketplace, tampilan **All Products** mobile
yang ringkas, serta filter tanggal ringkas untuk daftar Quotation/Invoice.
Desktop tetap memakai layout asli; filter tanggal tampil sebagai chip/popover.

Repo ini adalah **app Frappe mandiri** dengan nama app `frc_webshop`. Target:
Frappe/ERPNext 15–16 (lihat `pyproject.toml`).

## Isi

| File | Fungsi |
|------|--------|
| `pyproject.toml` | Metadata app yang dibaca bench/Frappe Cloud |
| `frc_webshop/hooks.py` | Hook asset, portal sidebar, dan invoice gate |
| `frc_webshop/webshop_shell.py` | Portal sidebar hook, `/orders` close, `/invoices` redirect gate |
| `frc_webshop/webshop_ui.py` | Endpoint aman `get_webshop_item_uoms` untuk detail Quotation |
| `frc_webshop/public/css/frc-webshop.css` | Styling shell, bottom nav, detail Quotation, List View mobile, chip/popover filter tanggal |
| `frc_webshop/public/js/frc-webshop.js` | Shell, bottom nav, builder detail, price/UOM decoration, filter tanggal server-side |
| `frc_webshop/setup/frc_webshop_local.py` | Setup/teardown lokal untuk 48 Customer FRC (idempoten) |
| `frc_webshop/tests/test_webshop_ui.py` | 70 test regresi UI + hook + gate |
| `docs/frc-webshop-quickstart.md` | Alur lokal FRC → Finance → Gudang |

## Pasang di bench

```bash
bench get-app https://github.com/callmevan1120/frc-webshop.git
bench --site <site> install-app frc_webshop
bench build --app frc_webshop
bench --site <site> clear-cache
```

`bench get-app` memakai nama app dari `pyproject.toml`, yaitu `frc_webshop`.

## Pasang di Frappe Cloud

1. Buka **Apps → Add app**, masukkan URL repo GitHub di atas.
2. Tunggu build selesai, lalu tambahkan app ke bench dan deploy.
3. Install app `frc_webshop` di site yang sudah memiliki ERPNext.

## Data dan setup

App ini hanya berisi UI dan hook; tidak membuat DocType/data baru dan tidak
mengubah Webshop Settings secara otomatis. Pastikan site sudah memiliki Webshop
Settings, Website Item, price list, dan user/customer FRC yang sesuai.

`frc_webshop/setup/frc_webshop_local.py` **hanya untuk site lokal `erp.localhost`**
dan akan menolak site lain. Jangan dijalankan di site online.

## Verifikasi

Test regresi dijalankan di app tujuan:

```bash
bench --site <site> run-tests --module frc_webshop.tests.test_webshop_ui
```

Pastikan 70 test lolos sebelum deploy. Sebagian test memakai data FRC lokal
(`erp.localhost`), jadi siapkan fixture yang sama bila dijalankan di site lain.

## Batasan desain

- Dibuat untuk storefront FRC; jangan dipakai di site lain tanpa menyesuaikan
  data Customer, Website Item, dan price list.
- `enable_checkout = 0`: tidak ada payment gateway. CTA tetap **Request for Quote**.
- Warna oranye `#ee4d2d` hanya untuk header/summary/banner/cart badge; tombol
  utama hitam.
- Harga, tanggal, dan status di detail **hanya** dari data Quotation yang ada.
- Admin/System Manager dibolehkan mengakses `/invoices`; Guest/non-FRC di-redirect
  302 ke `/all-products`.
- Filter tanggal daftar Quotation memakai `transaction_date`; daftar Invoice memakai
  `posting_date`. Filter dijalankan server-side lewat query param portal list.

## Status

Kode di repo ini disalin dari workspace lokal pada 2026-11-27 (v43). Belum ada
perubahan struktur Data, migrate, atau endpoint baru.
