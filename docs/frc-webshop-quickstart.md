# FRC Webshop → Quotation → Gated Fulfillment (erp.localhost)

## FRC (Portal)

1. Buka `http://erp.localhost:8080/all-products` dan login dengan email FRC masing-masing.
   Email mengikuti pola `frc<nomor customer>@erp.local`, misalnya `frc260158@erp.local`.
   Password uji lokal sama untuk semua FRC dan diberikan langsung oleh tim IT, tidak disimpan di repository ini.
2. Tambahkan `PJO2601` (Dry) dan/atau `PJ260010` (Frozen) ke keranjang.
3. Klik **Request for Quote**. ERPNext membuat Quotation submitted; tidak ada field pembayaran dan tidak ada Payment Gateway.

## Finance (Desk)

1. Buka Quotation hasil FRC.
2. Klik **Create → Sales Invoice**, lalu submit.
3. Klik **Create → Sales Order** dari Quotation yang sama, lalu submit.
4. Setelah transfer/DP terverifikasi, buat **Payment Entry** submitted untuk Sales Order:
   - Jika Sales Invoice dibuat dari Sales Order, PE boleh mereferensikan Sales Invoice.
   - Jika Sales Invoice dibuat dari Quotation sebelum Sales Order ada, PE harus mereferensikan **Sales Order** langsung. Sales Invoice tersebut tidak memiliki tautan `sales_order`, sehingga tidak melepas gate.
5. Sebelum PE submitted, Sales Order tidak muncul di `/gudang/fulfillment` dan generate ditolak dengan `PAYMENT_NOT_RELEASED`.

## Gudang

1. Buka `http://erp.localhost:8080/gudang/fulfillment`.
2. Sales Order yang sudah dibayar muncul di antrean. Klik **Generate**.
3. Sistem membuat Pick List **Dry** berisi `PJO2601` dan Pick List **Frozen** berisi `PJ260010`, keduanya draft.
4. Proses picking, packing, dan Delivery Note seperti biasa. Packing Slip dan label koli tidak berubah.

## Data uji yang dipakai

- Customer: `CUST-260158 — Harapan indah (FRC)`.
- Price List: `Harga Outlet`.
- Website warehouse: `Gudang Barang Jadi - JURI` untuk kedua item.
- Stock Dry `PJO2601` di `Gudang Barang Jadi - JURI` disiapkan lewat Material Receipt; Item Default-nya memakai akun inventory `1145.000 - Finished Good - JURI`.

## Rollback

Jalankan `warehouse_app.warehouse_app.setup.frc_webshop_local.teardown()` melalui `bench --site erp.localhost execute` untuk mencabut policy, portal user, Contact, Website Item, dan Item Price. Kode di-revert memakai tag `pre-frc-payment-gate`.
