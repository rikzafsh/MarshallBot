"""Uji unit mesin chatbot, pengurai tanggal, dan handler (tanpa Flask)."""
import csv
from datetime import date, datetime
from pathlib import Path

from chatbot import ChatbotEngine, load_themes
from chatbot.engine import preprocess, similarity, validate_theme
from chatbot.extractor import analisis, cari_bulan_jawa, cari_hari, cari_pasaran, mask_entitas
from chatbot.handlers import HANDLERS

BASE = Path(__file__).resolve().parent.parent
THEMES = load_themes(BASE / "themes")
TEMA = THEMES["marshall"]
SEKARANG = datetime(2026, 1, 15, 9, 0)      # Kamis Pahing, 26 Rejeb 1959


def bot():
    return ChatbotEngine(TEMA, handlers=HANDLERS)


def balas(pesan, terakhir=None):
    return bot().reply(pesan, terakhir=terakhir, sekarang=SEKARANG)


# --- praproses dan skor ------------------------------------------------------
def test_preprocess_normalisasi_dan_stopword():
    assert preprocess("Gmn cara hitung neptu, kak?") == ["bagaimana", "cara", "hitung", "neptu"]


def test_preprocess_tanggal_diganti_token():
    assert preprocess("Weton 17 Agustus 1945 apa?") == ["weton", "tglmasehi"]
    assert preprocess("Weton 3 Mei 2001 apa?") == ["weton", "tglmasehi"]


def test_preprocess_nama_diganti_jenisnya():
    assert preprocess("neptu Jumat Kliwon") == ["neptu", "namahari", "namapasaran"]


def test_similarity_kalimat_sama_bernilai_satu():
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
    assert analisis("10 Sela 1958").jawa[0].bulan == 11


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
def test_klasifikasi_intent():
    kasus = {
        "halo": "greeting",
        "Weton tanggal 17 Agustus 1945 apa?": "gregorian_to_weton",
        "Tanggal 17 Agustus 1945 masuk wuku apa?": "gregorian_to_wuku",
        "Kapan tanggal 1 Pasa tahun 1959?": "month_conversion",
        "Apa saja nama bulan Jawa?": "month_list",
        "gmn cara hitung neptu weton": "neptu_calculation",
        "Siapa yang memperkenalkan kalender Jawa Sultanagungan?": "sultan_agung",
    }
    b = bot()
    for pesan, harapan in kasus.items():
        assert b.classify(pesan)[0] == harapan, pesan


def test_variasi_tanggal_diarahkan_ke_intent_sama():
    """Lima variasi penulisan satu maksud (dokumen rancangan bagian 3.1)."""
    b = bot()
    for pesan in ["Tanggal 17 Agustus 1945 wetonnya apa?", "Weton untuk 17 Agustus 1945 apa?",
                  "Kalau tanggal 17 Agustus 1945, hari dan pasarannya apa?",
                  "Tanggal 17/08/1945 itu jatuh pada weton apa?",
                  "Coba cari weton tanggal 17 Agustus 1945."]:
        assert b.classify(pesan)[0] == "gregorian_to_weton", pesan


def test_salah_ketik_masih_dikenali():
    b = bot()
    assert b.classify("siklus pawukon bera hari")[0] == "pawukon_cycle"
    assert b.classify("pengertian wetonn")[0] == "weton_definition"


def test_pertanyaan_di_luar_tema_memberi_fallback():
    hasil = bot().reply("siapa pemenang piala dunia")
    assert hasil["intent"] is None
    assert hasil["reply"] in TEMA["fallback"]


def test_pesan_kosong():
    assert bot().reply("   ")["intent"] is None


def test_explain_tiga_kandidat_terurut():
    c = bot().explain("weton 17 Agustus 1945")
    assert len(c) == 3 and c[0]["score"] >= c[1]["score"] >= c[2]["score"]
    assert c[0]["intent"] == "gregorian_to_weton"


def test_validate_theme_menemukan_masalah():
    assert validate_theme({"id": "x"})
    rusak = dict(TEMA, intents=[
        {"tag": "a", "patterns": [], "responses": ["b"]},
        {"tag": "a", "patterns": ["p"], "responses": []},
        {"tag": "c", "patterns": ["p"], "responses": ["x"]}])
    masalah = validate_theme(rusak)
    assert any("lebih dari sekali" in m for m in masalah)
    assert any("ada di intent" in m for m in masalah)


def test_tema_marshall_valid_dan_lengkap():
    assert validate_theme(TEMA) == []
    assert len(TEMA["intents"]) == 46          # 47 di dokumen; CHAT006 Fallback = kunci "fallback"
    assert len(TEMA["suggestions"]) == 4
    for i in TEMA["intents"]:
        assert len(i["patterns"]) >= 4, i["tag"]


def test_semua_handler_terdaftar():
    for i in TEMA["intents"]:
        if "handler" in i:
            assert i["handler"] in HANDLERS, i["tag"]


def test_akurasi_data_uji_minimal_90_persen():
    b = ChatbotEngine(TEMA)
    with open(BASE / "evaluasi" / "marshall.csv", encoding="utf-8") as f:
        baris = list(csv.DictReader(f))
    benar = sum((b.classify(r["kalimat"])[0] or "fallback") == r["intent"] for r in baris)
    assert benar / len(baris) >= 0.90


# --- konversi kalender (memakai kalender.py hasil port farcode.js) -----------
def test_masehi_ke_jawa():
    r = balas("Tanggal 17 Agustus 1945 dalam kalender Jawa tanggal berapa?")
    assert "Jumat Legi, 9 Pasa 1876" in r["reply"] and r["status"] == "ok"


def test_masehi_ke_jawa_format_angka():
    assert "9 Pasa 1876" in balas("Ubah tanggal 17/08/1945 ke penanggalan Jawa")["reply"]


def test_jawa_ke_masehi():
    assert "27 Juni 2025" in balas("1 Sura 1959 itu tanggal Masehi berapa")["reply"]
    assert "18 Februari 2026" in balas("Kapan tanggal 1 Pasa tahun 1959?")["reply"]


def test_weton_dari_masehi_dan_jawa():
    r = balas("Weton tanggal 17 Agustus 1945 apa?")["reply"]
    assert "Jumat Legi" in r and "neptu 11" in r
    assert "Jumat Kliwon" in balas("1 Sura 1959 wetonnya apa")["reply"]


def test_wuku_dari_tanggal():
    assert "Manahil" in balas("Tanggal 17 Agustus 1945 masuk wuku apa?")["reply"]


def test_tanggal_jawa_hari_ini_dan_relatif():
    assert "Kamis Pahing, 26 Rejeb 1959" in balas("Apa tanggal Jawa hari ini?")["reply"]
    assert "Jumat Pon, 27 Rejeb 1959" in balas("Tanggal Jawa besok berapa")["reply"]
    assert "Rabu Legi, 25 Rejeb 1959" in balas("Tanggal Jawa kemarin")["reply"]


def test_rentang_tanggal():
    r = balas("Konversikan tanggal 1 sampai 3 Januari 2026 ke kalender Jawa.")["reply"]
    assert r.count("Rejeb 1959") == 3 and "1 Januari 2026" in r


def test_rentang_satu_bulan_penuh():
    r = balas("Konversi rentang 1 hingga 31 Januari 2026 ke kalender Jawa")
    assert r["status"] == "ok" and r["reply"].count("\n") == 31


def test_selisih_tanggal():
    assert "365" in balas("Selisih tanggal 17 Agustus 1945 dan 17 Agustus 1946")["reply"]
    r = balas("Hitung selisih hari 1 Sura 1959 dan 1 Sapar 1959")["reply"]
    assert " 30 hari" in r


def test_bulan_tahun_dan_windu_sekarang():
    assert "Rejeb" in balas("Sekarang bulan Jawa apa?")["reply"]
    assert "1959" in balas("Apa nama tahun Jawa sekarang?")["reply"] and "Dal" in balas("Tahun Jawa saat ini")["reply"]
    assert "Sancaya" in balas("Sekarang berada dalam windu apa?")["reply"]


def test_konversi_minta_tanggal_bila_kosong():
    r = balas("Konversi tanggal Masehi ke kalender Jawa")
    assert r["status"] == "perlu_info" and "17 Agustus 1945" in r["reply"]


def test_tanggal_masehi_tidak_valid_ditolak_sopan():
    r = balas("weton 31 Februari 2026")
    assert r["status"] == "perlu_info" and "tidak valid" in r["reply"]


def test_tanggal_jawa_yang_tidak_ada_ditolak_sopan():
    r = balas("Konversi 30 Sapar 1959 ke kalender Masehi")
    assert r["status"] == "perlu_info" and "tidak ada" in r["reply"]


# --- handler tabel -----------------------------------------------------------
def test_neptu_hari_pasaran_dan_weton():
    assert "3" in balas("Berapa nilai neptu hari Selasa?")["reply"]
    assert "8" in balas("neptu pasaran Kliwon")["reply"]
    assert "10" in balas("Neptu weton Selasa Pon berapa")["reply"]


def test_wuku_detail():
    assert "ke-1" in balas("Apa itu Wuku Sinta?")["reply"]
    assert "ke-30" in balas("jelaskan wuku Watugunung")["reply"]


def test_urutan_bulan():
    assert "Bakdamulud" in balas("Bulan apa setelah Mulud?")["reply"]
    assert "Besar" in balas("Bulan sebelum Sura apa")["reply"]
    assert "Sura" in balas("Setelah Besar bulan apa")["reply"]


def test_ulangi_jawaban():
    assert "35 hari" in balas("Bisa ulangi jawaban tadi?", terakhir="Selapan adalah 35 hari.")["reply"]
    assert balas("Bisa ulangi jawaban tadi?")["status"] == "perlu_info"


def test_placeholder_terisi():
    r = balas("halo")["reply"]
    assert "{" not in r and "MarshallBot" in r
