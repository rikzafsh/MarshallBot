# MarshallBot: Chatbot Konversi Kalender Jawa Mataraman

Chatbot tematik berbasis aturan (tanpa LLM) mengikuti kerangka praktikum
"Chatbot Tematik dengan Flask" (struktur `aplikasi-final`), dengan perhitungan
kalender yang di-port dari kode acuan `farcode.js`.

## Menjalankan

    python -m venv venv
    venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
    pip install -r requirements.txt
    python app.py                    # buka http://127.0.0.1:5000
    pytest -v                        # 62 uji
    python evaluate.py --sweep       # akurasi menurut ambang
    python cli.py --debug            # chat di terminal

Variabel lingkungan: `SECRET_KEY`, `ADMIN_KEY` (halaman /admin butuh `?key=...`),
`THRESHOLD` (bawaan 0.45), `DATABASE`. Produksi: `waitress-serve --port=8000 app:app`.

## Struktur

    app.py                    route halaman, REST API, admin
    cli.py, evaluate.py       chat terminal, ukur akurasi
    chatbot/engine.py         praproses, skor 0,4 J + 0,3 F + 0,3 C, ambang, load_themes
    chatbot/extractor.py      pengurai tanggal Masehi/Jawa/rentang, nama hari, pasaran, bulan, wuku
    chatbot/handlers.py       jawaban dinamis (konversi, neptu, wuku, urutan bulan)
    chatbot/kalender.py       PORT farcode.js: greg2jd, jd2jawa, jawa2jd, Pawukon
    chatbot/kalender_data.py  tabel hari, pasaran, neptu, bulan, wuku, windu
    chatbot/database.py       riwayat dan statistik SQLite
    themes/marshall.json      46 intent, 264 pola (CHAT006 Fallback = kunci "fallback")
    evaluasi/marshall.csv     58 kalimat uji
    tests/                    test_kalender (golden dari farcode.js), test_engine, test_app

## Tentang perhitungan kalender

`kalender.py` memakai rumus dan konstanta `farcode.js` apa adanya. Hasil Python
dibandingkan dengan JavaScript asli pada 219.145 hari (1700 sampai 2299): identik.
`tests/golden_farcode.json` berisi 478 tanggal hasil Node untuk menjaga hal ini.

Catatan penting: pada kode acuan, `jd2jawa` memakai 354,36667 sedangkan `jawa2jd`
memakai 354,35. Akibatnya pada tahun Jimakir keduanya berbeda satu hari
(Jimakir 355 hari menurut `jawa2jd`, 354 hari menurut `jd2jawa`). Di luar
Jimakir keduanya konsisten. MarshallBot memakai `jd2jawa` untuk Masehi ke Jawa
dan `jawa2jd` untuk Jawa ke Masehi, persis seperti acuan.

## Menambah pola

Lihat `/admin/marshall`, salin pertanyaan "tidak dikenali" ke `patterns` intent
yang sesuai di `themes/marshall.json`, lalu jalankan `pytest` dan `python evaluate.py`.
