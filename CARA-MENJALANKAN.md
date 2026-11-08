# MarshallBot: Chatbot Konversi Kalender Jawa Mataraman

Chatbot tematik berbasis aturan (tanpa LLM), dibangun dengan Flask mengikuti
struktur praktikum "Chatbot Tematik dengan Flask".

## Menjalankan

    python -m venv venv
    venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
    pip install -r requirements.txt
    python app.py                    # buka http://127.0.0.1:5000
    pytest -v                        # jalankan uji
    python evaluate.py --sweep       # akurasi menurut ambang
    python cli.py --debug            # chat di terminal

Variabel lingkungan: `SECRET_KEY`, `ADMIN_KEY` (halaman /admin butuh `?key=...`),
`THRESHOLD` (bawaan 0.45), `DATABASE`, `FLASK_DEBUG=1` (hanya di komputer sendiri).
Produksi: `waitress-serve --port=8000 --call app:create_app`.

## Struktur

    app.py                 route halaman, REST API, admin
    chatbot/engine.py      praproses, skor (0,4 Jaccard + 0,3 Fuzzy + 0,3 Cakupan), ambang
    chatbot/extractor.py   pengurai tanggal Masehi/Jawa/rentang, nama hari, pasaran, bulan, wuku
    chatbot/handlers.py    jawaban dinamis (neptu, wuku, urutan bulan, konversi)
    chatbot/kalender.py    >>> TEMPAT KODE ACUAN KONVERSI <<<
    chatbot/kalender_data.py  tabel hari, pasaran, neptu, bulan, wuku, windu
    chatbot/database.py    riwayat dan statistik SQLite
    themes/marshall.json   46 intent, 264 pola (CHAT006 Fallback = kunci "fallback")
    evaluasi/marshall.csv  kalimat uji; tests/  uji pytest

## Memasang kode acuan konversi

Isi dua fungsi di `chatbot/kalender.py`:

- `gregorian_to_javanese(tgl: date) -> TanggalJawa`
- `javanese_to_gregorian(tanggal, bulan, tahun) -> date`  (bulan 1..12, 1 = Sura)

`TanggalJawa` memuat tanggal, bulan, tahun, hari, pasaran, wuku, nama_tahun, windu.
Setelah terisi, otomatis aktif: CONV001 sampai CONV008, MON004, MON006,
YEAR001, YEAR008. Lalu ubah uji `test_konversi_belum_aktif_selama_stub`.
`test_alur_konversi_dengan_kalender_tiruan` membuktikan alur jawabannya sudah benar.

## Menambah pola

Lihat halaman `/admin/marshall`, salin pertanyaan "tidak dikenali" ke `patterns`
intent yang sesuai di `themes/marshall.json`, lalu jalankan `pytest` dan `python evaluate.py`.
