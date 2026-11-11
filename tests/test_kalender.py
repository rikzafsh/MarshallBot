"""Uji perhitungan kalender Jawa: harus identik dengan kode acuan farcode.js."""
import json
from datetime import date, timedelta
from pathlib import Path

from chatbot import kalender as k

GOLDEN = json.loads((Path(__file__).parent / "golden_farcode.json").read_text())


def test_identik_dengan_farcode_js():
    """Data golden dihasilkan langsung dari farcode.js (Node) untuk ratusan tanggal."""
    for r in GOLDEN:
        jd = k.greg2jd(*r["masehi"])
        assert jd == r["jd"], r["masehi"]
        assert list(k.jd2jawa(jd)) == r["jawa"], r["masehi"]
        assert k.jd2np(jd) == r["np"], r["masehi"]
        assert k.np2w7(r["np"]) == r["w7"] and k.np2w5(r["np"]) == r["w5"]
        assert k.np2wuku(r["np"]) == r["wuku"]


def test_jawa2jd_identik_dengan_farcode_js():
    for r in GOLDEN:
        tahun, bulan, tanggal = r["jawa"]
        assert k.jawa2jd(tanggal, bulan, tahun) == r["jawa2jd"], r["masehi"]


def test_proklamasi_jumat_legi_9_pasa_1876():
    t = k.gregorian_to_javanese(date(1945, 8, 17))
    assert (t.weton, t.tanggal, t.nama_bulan, t.tahun) == ("Jumat Legi", 9, "Pasa", 1876)
    assert t.neptu == 11 and t.wuku == "Manahil"


def test_tanggal_acuan_lain():
    assert k.gregorian_to_javanese(date(2000, 1, 1)).weton == "Sabtu Legi"
    assert k.gregorian_to_javanese(date(2026, 1, 1)).weton == "Kamis Pon"


def test_satu_sura_tahun_baru_jawa():
    """1 Sura 1957 sampai 1959 sesuai penetapan tahun baru Jawa yang lazim."""
    kasus = {1956: (date(2022, 7, 30), "Sabtu Pahing"), 1957: (date(2023, 7, 20), "Kamis Pahing"),
             1959: (date(2025, 6, 27), "Jumat Kliwon")}
    for tahun, (tgl, weton) in kasus.items():
        assert k.javanese_to_gregorian(1, 1, tahun) == tgl
        assert k.gregorian_to_javanese(tgl).weton == weton


def test_nama_tahun_dan_windu():
    t = k.gregorian_to_javanese(date(2026, 1, 1))
    assert (t.tahun, t.nama_tahun, t.windu) == (1959, "Dal", "Sancaya")
    assert k.nomor_tahun_dalam_windu(1555) == 1      # 1 Sura 1555 = tahun Alip (Sultan Agung)


def test_wuntu_adalah_ehe_dal_jimakir():
    nama = {k.nomor_tahun_dalam_windu(y): k.panjang_tahun(y) for y in range(1955, 1963)}
    assert [n for n, p in nama.items() if p == 355] == [2, 5, 8]   # Ehe, Dal, Jimakir
    assert sum(k.panjang_tahun(y) for y in range(1955, 1963)) == 2835


def test_bulan_berselang_30_dan_29_hari():
    assert [k.panjang_bulan(b, 1958) for b in range(1, 13)] == [30, 29] * 6   # wastu
    assert k.panjang_bulan(12, 1959) == 30                                      # wuntu


def test_tanggal_jawa_tidak_ada_ditolak():
    for args in [(30, 2, 1959), (30, 12, 1958), (31, 1, 1959), (0, 1, 1959), (1, 13, 1959)]:
        try:
            k.javanese_to_gregorian(*args)
        except k.TanggalTidakValid:
            continue
        raise AssertionError(f"{args} seharusnya ditolak")
    assert k.javanese_to_gregorian(30, 12, 1959)       # 30 Besar sah di tahun wuntu


def test_bolak_balik_konsisten_kecuali_tahun_jimakir():
    """Catatan kode acuan: jd2jawa memakai 354,36667 dan jawa2jd 354,35, sehingga
    pada tahun Jimakir keduanya berbeda satu hari. Uji ini mendokumentasikan hal itu;
    bila konstanta diselaraskan, ubah menjadi 'konsisten untuk semua tahun'."""
    tak_cocok_bukan_jimakir = 0
    d = date(1900, 1, 1)
    while d < date(2100, 1, 1):
        t = k.gregorian_to_javanese(d)
        kembali = k.jawa2jd(t.tanggal, t.bulan, t.tahun)
        if kembali != k.greg2jd(d.year, d.month, d.day) and t.nama_tahun != "Jimakir":
            tak_cocok_bukan_jimakir += 1
        d += timedelta(days=3)
    assert tak_cocok_bukan_jimakir == 0
