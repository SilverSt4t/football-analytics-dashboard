# Touchline — Dashboard Sepak Bola

Dashboard analisis sepak bola interaktif berbasis Streamlit dan OpenLigaDB API.

## Fitur

- Filter kompetisi dan musim dari sidebar.
- Ringkasan KPI: pertandingan selesai, total gol, rata-rata gol, dan kemenangan kandang.
- Grafik hasil pertandingan dan tren gol per pekan.
- Halaman jadwal/hasil dengan filter tim, pekan, dan status.
- Klasemen serta grafik gol per tim.
- Daftar pencetak gol.
- Cache API 15 menit, tombol muat ulang, dan snapshot Premier League sebagai fallback bila API sedang tidak tersedia.
- Waktu pertandingan ditampilkan dalam WIB.

## Struktur

- `app.py` — aplikasi Streamlit
- `data/` — snapshot Premier League 2026/27 untuk fallback offline
- `requirements.txt` — dependensi
