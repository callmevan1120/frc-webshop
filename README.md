# FRC Webshop — custom storefront for Frappe/ERPNext

Kustomisasi **storefront FRC** di atas Webshop ERPNext: satu shell portal yang rapi,
halaman detail Quotation bergaya marketplace, dan tampilan **All Products** mobile
yang ringkas. Desktop sengaja tidak diubah.

Repo ini adalah **kumpulan file kustom** yang dipakai di app `warehouse_app` pada
site `erp.localhost`. Bukan app Frappe mandiri — cara pasangnya ada di bawah.

## Isi

| File | Fungsi |
|------|--------|
| `frc_webshop/public/css/frc-webshop.css` | Styling shell, bottom nav, detail Quotation, List View mobile |
| `frc_webshop/public/js/frc-webshop.js` | Shell, bottom nav, builder detail, price/UOM decoration |
| `frc_webshop/webshop_shell.py` | Portal sidebar hook, `/orders` close, `/invoices` redirect gate |
| `frc_webshop/webshop_ui.py` | Endpoint aman `get_webshop_item_uoms` untuk detail Quotation |
| `frc_webshop/setup/frc_webshop_local.py` | Setup/teardown lokal untuk 48 Customer FRC (idempoten) |
| `frc_webshop/tests/test_webshop_ui.py` | 49 test regresi UI + hook + gate |
| `hooks_webshop.py` | Cuplikan hook yang perlu ditambahkan ke `hooks.py` appFrappe Anda |
| `docs/frc-webshop-quickstart.md` | Alur FRC → Finance → Gudang |

## Pasang di app Frappe

1. Salin isi folder `frc_webshop/` ke dalam app Frappe Anda, misalnya
   `warehouse_app/frc_webshop/` (sesuaikan import path di hook bila perlu).
2. Salin atau gabungkan isi `hooks_webshop.py` ke `hooks.py` app tersebut.
3. Setiap kali mengubah JS/CSS, **bump `?v=`** pada `web_include_css` dan
   `web_include_js` supaya browser tidak memakai cache lama.
4. Deploy: `bench build`, restart backend, lalu
   `bench --site <site> clear-cache`.

## Batasan desain

- Hanya `erp.localhost`. Jangan dipakai di `fulfillment.localhost` atau produksi
  tanpa penyesuaian.
- `enable_checkout = 0`: tidak ada payment gateway. CTA tetap **Request for Quote**.
- Warna oranye `#ee4d2d` hanya untuk header/summary/banner/cart badge; tombol
  utama hitam.
- Harga, tanggal, dan status di detail **hanya** dari data Quotation yang ada.
- Admin/System Manager dibolehkan mengakses `/invoices`; Guest/non-FRC di-redirect
  302 ke `/all-products`.

## Verifikasi

Test regresi dijalankan di app tujuan:

```bash
bench --site erp.localhost run-tests --module <app>.tests.test_webshop_ui
```

Pastikan 49 test lolos sebelum deploy.

## Status

Kode di repo ini disalin dari workspace lokal pada 2026-11-25 (v23). Belum ada
perubahan struktur Data, migrate, atau endpoint baru.
