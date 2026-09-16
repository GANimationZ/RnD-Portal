# Migrasi SQLite -> PostgreSQL

Struktur database sudah disiapkan supaya migrasi ini tinggal ganti
konfigurasi, tanpa ubah kode:

- Semua model (`library/models.py`) pakai tipe kolom generik SQLAlchemy
  (Integer, String, Float, Date, DateTime, Text, Boolean) -- tidak ada
  fitur khusus SQLite.
- Data historis KPI (`KPIRecord`) disimpan ternormalisasi per baris,
  bukan JSON blob, supaya nyaman di-query native di Postgres.
- Dummy data (`library/seed.py`) masuk lewat model SQLAlchemy biasa,
  jadi berlaku sama persis di SQLite maupun Postgres.

## Langkah migrasi

1. Install driver Postgres:
   ```bash
   pip install psycopg2-binary
   ```
   (atau uncomment baris `psycopg2-binary` di `requirements.txt`)

2. Buat database kosong di PostgreSQL, mis:
   ```sql
   CREATE DATABASE rnd_portal;
   ```

3. Set environment variable `DATABASE_URL` sebelum menjalankan app:
   ```bash
   export DATABASE_URL="postgresql+psycopg2://user:password@host:5432/rnd_portal"
   python app.py
   ```
   Kalau `DATABASE_URL` tidak di-set, aplikasi otomatis fallback ke
   SQLite lokal (`sqlite:///database.db`) seperti sebelumnya -- jadi
   aman untuk development tanpa server Postgres.

4. Saat pertama kali jalan dengan `DATABASE_URL` baru, `app.py` akan
   otomatis memanggil `db.create_all()` (bikin semua tabel) dan
   `seed_dummy_data()` (isi dummy data awal -- no-op kalau tabel
   `employees` sudah ada isinya).

5. Kalau nanti butuh histori perubahan skema (migration files) untuk
   tim yang lebih besar, tinggal tambah `Flask-Migrate`:
   ```bash
   pip install Flask-Migrate
   ```
   lalu inisialisasi `flask db init/migrate/upgrade` seperti biasa --
   model yang sudah ada tidak perlu diubah.

Tidak ada satupun query di `routes.py` / `metrics.py` yang pakai sintaks
SQL mentah atau fitur spesifik SQLite, jadi tidak ada logic yang perlu
ditulis ulang saat pindah dialect database.
