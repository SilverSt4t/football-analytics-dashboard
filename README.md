# Touchline — Football Analytics Dashboard

Dashboard sepak bola dengan arsitektur **backend dan frontend terpisah**, dan sumber data **hanya OpenLigaDB API**. Tidak ada unggah data manual, pembacaan CSV/JSON lokal, atau file data mentah. Respons API diproses di memori; cache hanya menyimpan data yang sudah dinormalisasi selama 15 menit. Jika API gagal, dashboard menampilkan pesan error dan tidak mengganti data dengan file fallback.

## Arsitektur

```text
OpenLigaDB API
      ↓
backend/ — FastAPI REST API + normalisasi + cache data bersih
      ↓ HTTP
frontend/ — Streamlit UI/UX
```

### Backend

- `backend/main.py` — endpoint REST FastAPI.
- `backend/get_data.py` — panggil API, normalisasi JSON di memori, cache hasil normalisasi, serta pilih URL logo tim dari sumber yang diizinkan.
- `backend/competition_catalog.py` — katalog terkurasi kompetisi papan atas (liga domestik utama dan turnamen internasional). API tetap menentukan kompetisi mana yang benar-benar muncul untuk tiap musim.
- Logo dipilih berurutan dari Wikimedia, host gambar tepercaya yang disediakan API (mis. UEFA/DFB/Kicker), lalu gambar kecil yang tertanam di respons API. URL diproxy backend; gambar inline hanya diproses di memori. Jika tetap tidak ditemukan, UI memakai inisial tim.

Endpoint utama:

- `GET /health` — status backend.
- `GET /api/leagues/{season}` — daftar kompetisi dari API.
- `GET /api/competitions/{shortcut}/{season}` — jadwal, klasemen, pencetak gol dari API.
- `GET /api/assets/team-logo?url=...` — proxy logo dari daftar domain gambar yang diizinkan.
- `GET /docs` — dokumentasi interaktif Swagger.

### Frontend

- `frontend/app.py` — dashboard Streamlit dengan filter kompetisi dan navigasi horizontal di area utama (sidebar tidak dipakai untuk kontrol). Ringkasan, jadwal, klasemen, pencetak gol, statistik pemain, dan panel personal dipisahkan; pertandingan dikelompokkan per pekan.
- `frontend/api_client.py` — client HTTP untuk mengambil data dari backend.

## Menjalankan lokal dengan satu perintah

Pasang dependensi sekali dari folder proyek:

```bash
python -m pip install -r requirements.txt
```

Aktifkan virtual environment yang berisi dependensi, buka CMD di folder `football_dashboard`, lalu jalankan:

```cmd
python main.py
```

Launcher menjalankan backend dan frontend, menunggu keduanya siap, lalu membuka dashboard di `http://127.0.0.1:8501`. Tekan `Ctrl+C` di CMD untuk menghentikan keduanya. Dokumentasi backend tersedia di `http://127.0.0.1:8000/docs`.

Kalau ingin menjalankan layanan secara manual, backend dan frontend tetap bisa dijalankan terpisah seperti biasa.

Tidak perlu API key OpenLigaDB. Karena tidak ada data fallback, dashboard memerlukan koneksi ke backend dan OpenLigaDB agar dapat menampilkan data. Data komunitas disajikan untuk eksplorasi; cakupan kompetisi/statistik dapat berbeda. Beri atribusi dan periksa [lisensi OpenLigaDB](https://www.openligadb.de/lizenz) bila menggunakan ulang atau menyebarkan data.
