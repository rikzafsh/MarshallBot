"""Uji unit mesin chatbot, pengurai tanggal, dan handler."""
import json
from datetime import date, datetime
from pathlib import Path

from chatbot import kalender
from chatbot.engine import ChatbotEngine, preprocess, similarity, validate_theme
from chatbot.extractor import analisis, cari_bulan_jawa, cari_hari, cari_pasaran, mask_entitas
from chatbot.handlers import HANDLERS
from chatbot.kalender import TanggalJawa

TEMA = json.loads((Path(__file__).parent.parent / "themes" / "marshall.json").read_text(encoding="utf-8"))
SEKARANG = datetime(2026, 1, 15, 9, 0)


def bot():
    return ChatbotEngine(TEMA, handlers=HANDLERS)


# --- praproses dan skor ------------------------------------------------------
def test_preprocess_normalisasi_dan_stopword():
    assert preprocess("Gmn cara hitung neptu, kak?") == ["bagaimana", "cara", "hitung", "neptu"]


def test_preprocess_tanggal_diganti_token():
    assert preprocess("Weton 17 Agustus 1945 apa?") == ["weton", "tglmasehi"]
    assert preprocess("Weton 3 Mei 2001 apa?") == ["weton", "tglmasehi"]


def test_preprocess_nama_diganti_jenisnya():
    assert preprocess("neptu Jumat Kliwon") == ["neptu", "namahari", "namapasaran"]


def test_similarity_sama_bernilai_satu():
    t = preprocess("cara hitung neptu")
    assert similarity(t, t) == 1.0


def test_similarity_kalimat_berbeda_rendah():
    assert similarity(preprocess("cara hitung neptu"), preprocess("sejarah sultan agung")) < 0.45


# --- pengurai tanggal --------------------------------------------------------
def test_tanggal_masehi_berbagai_format():
    for teks in ("17 Agustus 1945", "17/08/1945", "17-08-1945", "17 agu 1945"):
        assert analisis(teks).masehi == [date(1945, 8, 17)], teks


def test_tanggal_jawa_dengan_dan_tanpa_tahun():
    e = analisis("1 Sura tahun 1959")
    assert (e.jawa[0].tanggal, e.jawa[0].bulan, e.jawa[0].tahun) == (1, 1, 1959)
    assert analisis("apa weton tanggal 1 Sura").jawa[0].tahun is None


def test_rentang_tanggal():
    assert analisis("1 sampai 10 Januari 2026").rentang == (date(2026, 1, 1), date(2026, 1, 10))
    assert mask_entitas("1 - 10 Januari 2026") == "tglrentang"


def test_tanggal_tidak_valid_dicatat():
    assert analisis("31 Februari 2026").salah == ["31 Februari 2026"]


def test_besar_hanya_bulan_bila_ada_angka_atau_kata_bulan():
    assert analisis("ukuran besar").jawa == []
    assert analisis("10 Besar 1958").jawa[0].bulan == 12
    assert cari_bulan_jawa("bulan Besar") == ["Besar"]
    assert cari_bulan_jawa("ukuran besar") == []


def test_cari_hari_dan_pasaran_dengan_ejaan_jawa():
    assert cari_hari("neptu Rebo") == ["Rabu"]
    assert cari_pasaran("weton Jemuwah Kliwon") == ["Kliwon"]


# --- klasifikasi -------------------------------------------------------------
def intent_dari(pesan):
    return bot().classify(pesan)[0]


def test_klasifikasi_inti():
    kasus = {
        "halo": "greeting",
        "Weton tanggal 17 Agustus 1945 apa?": "gregorian_to_weton",
        "Tanggal 17 Agustus 1945 masuk wuku apa?": "gregorian_to_wuku",
        "Kapan tanggal 1 Pasa tahun 1959?": "month_conversion",
        "Apa saja nama bulan Jawa?": "month_list",
        "gmn cara hitung neptu weton": "neptu_calculation",
        "Siapa yang memperkenalkan kalender Jawa Sultanagungan?": "sultan_agung",
    }
    for pesan, harapan in kasus.items():
        assert intent_dari(pesan) == harapan, pesan


def test_variasi_tanggal_diarahkan_ke_intent_sama():
    """Contoh dokumen rancangan bagian 3.1: lima variasi satu intent."""
    for pesan in ["Tanggal 17 Agustus 1945 wetonnya apa?", "Weton untuk 17 Agustus 1945 apa?",
                  "Kalau tanggal 17 Agustus 1945, hari dan pasarannya apa?",
                  "Tanggal 17/08/1945 itu jatuh pada weton apa?",
                  "Coba cari weton tanggal 17 Agustus 1945."]:
        assert intent_dari(pesan) == "gregorian_to_weton", pesan


def test_salah_ketik_masih_dikenali():
    assert intent_dari("siklus pawukon bera hari") == "pawukon_cycle"
    assert intent_dari("pengertian wetonn") == "weton_definition"


def test_di_luar_tema_mendapat_fallback():
    r = bot().reply("siapa pemenang piala dunia")
    assert r["intent"] is None and r["reply"] in TEMA["fallback"]


def test_explain_menghasilkan_tiga_kandidat_terurut():
    c = bot().explain("weton 17 Agustus 1945")
    assert len(c) == 3 and c[0]["score"] >= c[1]["score"] >= c[2]["score"]
    assert c[0]["above_threshold"] is True


def test_validate_theme_menemukan_kesalahan():
    assert validate_theme({"id": "x"})
    rusak = {"id": "x", "bot_name": "X", "title": "X", "fallback": ["a"],
             "intents": [{"tag": "a", "patterns": [], "responses": ["b"]},
                         {"tag": "a", "patterns": ["p"], "responses": []}]}
    assert len(validate_theme(rusak)) == 3


def test_tema_marshall_valid_dan_lengkap():
    assert validate_theme(TEMA) == []
    assert len(TEMA["intents"]) == 46          # 47 di dokumen; CHAT006 = fallback tema
    for i in TEMA["intents"]:
        assert len(i["patterns"]) >= 4, i["tag"]


def test_akurasi_data_uji_minimal_90_persen():
    import csv
    b = bot()
    with open(Path(__file__).parent.parent / "evaluasi" / "marshall.csv", encoding="utf-8") as f:
        baris = list(csv.DictReader(f))
    benar = sum((b.classify(r["kalimat"])[0] or "fallback") == r["intent"] for r in baris)
    assert benar / len(baris) >= 0.90


# --- handler aktif (tabel) ---------------------------------------------------
def balas(pesan, terakhir=None):
    return bot().reply(pesan, terakhir=terakhir, sekarang=SEKARANG)


def test_neptu_hari_pasaran_dan_weton():
    assert "3" in balas("Berapa nilai neptu hari Selasa?")["reply"]
    assert "8" in balas("neptu pasaran Kliwon")["reply"]
    assert "10" in balas("Neptu weton Selasa Pon berapa")["reply"]


def test_wuku_detail():
    r = balas("Apa itu Wuku Sinta?")
    assert "ke-1" in r["reply"] and "membuka" in r["reply"]
    assert "ke-30" in balas("jelaskan wuku Watugunung")["reply"]


def test_urutan_bulan():
    assert "Bakdamulud" in balas("Bulan apa setelah Mulud?")["reply"]
    assert "Besar" in balas("Bulan sebelum Sura apa")["reply"]
    assert "Sura" in balas("Setelah Besar bulan apa")["reply"]


def test_ulangi_jawaban():
    assert "Selapanan" in balas("Bisa ulangi jawaban tadi?", terakhir="Selapanan adalah 35 hari.")["reply"]
    assert balas("Bisa ulangi jawaban tadi?")["status"] == "perlu_info"


def test_placeholder_nama_bot_dan_salam_terisi():
    r = balas("halo")["reply"]
    assert "{" not in r and "MarshallBot" in r


# --- konversi: sebelum dan sesudah kode acuan masuk --------------------------
def test_konversi_belum_aktif_selama_stub():
    """Hapus/ubah uji ini setelah kalender.py diisi kode acuan."""
    r = balas("Konversi 17 Agustus 1945 ke kalender Jawa")
    assert r["intent"] == "gregorian_to_javanese" and r["status"] == "perhitungan_belum_aktif"


def test_konversi_minta_tanggal_bila_kosong():
    r = balas("Konversi tanggal Masehi ke kalender Jawa")
    assert r["status"] == "perlu_info" and "17 Agustus 1945" in r["reply"]


def test_tanggal_tidak_valid_ditolak_sopan():
    r = balas("weton 31 Februari 2026")
    assert r["status"] == "perlu_info" and "tidak valid" in r["reply"]


def test_selisih_dua_tanggal_masehi_sudah_berfungsi():
    r = balas("Selisih tanggal 17 Agustus 1945 dan 17 Agustus 1946")
    assert "365" in r["reply"]


def test_alur_konversi_dengan_kalender_tiruan(monkeypatch):
    """Membuktikan handler dan template jawaban bekerja begitu kalender.py aktif."""
    palsu = TanggalJawa(tanggal=1, bulan=1, tahun=1959, hari="Jumat", pasaran="Legi",
                        wuku="Sinta", nama_tahun="Alip", windu="Adi")
    monkeypatch.setattr(kalender, "gregorian_to_javanese", lambda d: palsu)
    monkeypatch.setattr(kalender, "javanese_to_gregorian", lambda t, b, y: date(2026, 6, 17))
    assert "Jumat Legi" in balas("Weton 17 Agustus 1945")["reply"]
    assert "neptu 11" in balas("Weton 17 Agustus 1945")["reply"]
    assert "Sinta" in balas("17 Agustus 1945 masuk wuku apa")["reply"]
    assert "17 Juni 2026" in balas("1 Sura 1959 itu tanggal Masehi berapa")["reply"]
    r = balas("Konversikan tanggal 1 sampai 3 Januari 2026 ke kalender Jawa")["reply"]
    assert r.count("1 Sura 1959") == 3
    assert "Sura" in balas("Sekarang bulan Jawa apa?")["reply"]
    assert "1959" in balas("Tahun Jawa sekarang apa?")["reply"]
