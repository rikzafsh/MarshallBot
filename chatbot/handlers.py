"""Handler untuk intent dinamis.

Setiap handler menerima Konteks dan mengembalikan dict isian untuk placeholder
di template respons (file tema), misalnya {"input": "...", "hasil": "..."}.
Handler boleh melempar:
- PerluInfo(pesan)         : data dari pengguna kurang, tanyakan balik;
- KalenderBelumTersedia    : perhitungan di kalender.py belum diisi.

Dua kelompok handler:
- Pencarian tabel (neptu, wuku, urutan bulan): sudah berfungsi penuh.
- Konversi tanggal: memanggil kalender.py, aktif otomatis saat kode acuan masuk.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from . import kalender
from .engine import Konteks, PerluInfo
from .extractor import (
    analisis, cari_bulan_jawa, cari_hari, cari_pasaran, cari_wuku,
    format_tanggal, TglJawa,
)
from .kalender_data import (
    BULAN_JAWA, NEPTU_HARI, NEPTU_PASARAN, WUKU,
)

MAKS_RENTANG_HARI = 62

CONTOH_MASEHI = "Contoh: 17 Agustus 1945 atau 17/08/1945."
CONTOH_JAWA = "Contoh: 1 Sura 1959."


# --- Pembantu ----------------------------------------------------------------

def _tanggal_masehi(k: Konteks) -> tuple[date, str]:
    """Tanggal Masehi dari pesan; 'hari ini/besok/kemarin' ikut dikenali."""
    ent = analisis(k.pesan)
    if ent.salah:
        raise PerluInfo(f"Tanggal \"{ent.salah[0]}\" tidak valid. {CONTOH_MASEHI}")
    if ent.masehi:
        d = ent.masehi[0]
        return d, format_tanggal(d)
    if ent.relatif is not None:
        d = k.sekarang.date() + timedelta(days=ent.relatif)
        return d, format_tanggal(d)
    raise PerluInfo(f"Tanggal Masehi mana yang ingin Anda cek? {CONTOH_MASEHI}")


def _tanggal_jawa(k: Konteks, butuh_tahun: bool = True) -> TglJawa:
    ent = analisis(k.pesan)
    if ent.salah:
        raise PerluInfo(f"Tanggal \"{ent.salah[0]}\" tidak valid. {CONTOH_JAWA}")
    if not ent.jawa:
        raise PerluInfo(f"Tanggal Jawa mana yang ingin Anda cek? {CONTOH_JAWA}")
    tj = ent.jawa[0]
    if tj.tahun is None and butuh_tahun:
        # Tanpa tahun: pakai tahun Jawa yang sedang berjalan.
        tj = TglJawa(tj.tanggal, tj.bulan, kalender.gregorian_to_javanese(k.sekarang.date()).tahun)
    return tj


def _ke_masehi(tj: TglJawa) -> date:
    return kalender.javanese_to_gregorian(tj.tanggal, tj.bulan, tj.tahun)


# --- Konversi (memanggil kalender.py) ----------------------------------------

def gregorian_to_javanese(k: Konteks) -> dict:
    d, teks = _tanggal_masehi(k)
    return {"input": teks, "hasil": kalender.gregorian_to_javanese(d).teks()}


def javanese_to_gregorian(k: Konteks) -> dict:
    tj = _tanggal_jawa(k)
    return {"input": tj.teks() if tj.tahun else f"{tj.tanggal} {BULAN_JAWA[tj.bulan - 1]}",
            "hasil": format_tanggal(_ke_masehi(tj))}


def gregorian_to_weton(k: Konteks) -> dict:
    d, teks = _tanggal_masehi(k)
    tj = kalender.gregorian_to_javanese(d)
    return {"input": teks, "hasil": tj.weton, "neptu": str(tj.neptu)}


def javanese_to_weton(k: Konteks) -> dict:
    tj = _tanggal_jawa(k)
    jw = kalender.gregorian_to_javanese(_ke_masehi(tj))
    return {"input": tj.teks(), "hasil": jw.weton, "neptu": str(jw.neptu)}


def gregorian_to_wuku(k: Konteks) -> dict:
    d, teks = _tanggal_masehi(k)
    return {"input": teks, "hasil": kalender.gregorian_to_javanese(d).wuku}


def tanggal_jawa_hari_ini(k: Konteks) -> dict:
    ent = analisis(k.pesan)
    selisih = ent.relatif if ent.relatif is not None else 0
    d = k.sekarang.date() + timedelta(days=selisih)
    label = {0: "Hari ini", 1: "Besok", 2: "Lusa", -1: "Kemarin"}.get(selisih, "Tanggal itu")
    return {"label": label, "input": format_tanggal(d),
            "hasil": kalender.gregorian_to_javanese(d).teks()}


def konversi_rentang(k: Konteks) -> dict:
    ent = analisis(k.pesan)
    if ent.salah:
        raise PerluInfo(f"Rentang \"{ent.salah[0]}\" tidak valid. "
                        "Contoh: 1 sampai 10 Januari 2026.")
    if not ent.rentang:
        raise PerluInfo("Rentang tanggal mana yang ingin dikonversi? "
                        "Contoh: 1 sampai 10 Januari 2026.")
    awal, akhir = ent.rentang
    jumlah = (akhir - awal).days + 1
    if jumlah > MAKS_RENTANG_HARI:
        raise PerluInfo(f"Rentang terlalu panjang ({jumlah} hari). "
                        f"Maksimal {MAKS_RENTANG_HARI} hari sekali konversi.")
    baris = []
    for i in range(jumlah):
        d = awal + timedelta(days=i)
        baris.append(f"{format_tanggal(d)}: {kalender.gregorian_to_javanese(d).teks()}")
    return {"hasil": "\n" + "\n".join(baris)}


def selisih_tanggal(k: Konteks) -> dict:
    ent = analisis(k.pesan)
    if ent.salah:
        raise PerluInfo(f"Tanggal \"{ent.salah[0]}\" tidak valid.")
    daftar = [(jenis, nilai) for jenis, nilai in ent.urutan if jenis in ("masehi", "jawa")]
    if len(daftar) < 2:
        raise PerluInfo("Sebutkan dua tanggal. Contoh: selisih 1 Sura 1959 dan "
                        "1 Sapar 1959, atau 17 Agustus 1945 dan 17 Agustus 1946.")
    hasil: list[date] = []
    for jenis, nilai in daftar[:2]:
        if jenis == "masehi":
            hasil.append(nilai)
        else:
            tj = nilai if nilai.tahun else _tanggal_jawa_tahun_ini(k, nilai)
            hasil.append(_ke_masehi(tj))
    return {"hasil": str(abs((hasil[1] - hasil[0]).days))}


def _tanggal_jawa_tahun_ini(k: Konteks, tj: TglJawa) -> TglJawa:
    return TglJawa(tj.tanggal, tj.bulan, kalender.gregorian_to_javanese(k.sekarang.date()).tahun)


def bulan_jawa_sekarang(k: Konteks) -> dict:
    return {"hasil": kalender.gregorian_to_javanese(k.sekarang.date()).nama_bulan}


def konversi_bulan(k: Konteks) -> dict:
    """'Kapan tanggal 1 Pasa tahun 1959?' -> tanggal Masehi."""
    return javanese_to_gregorian(k)


def tahun_jawa_sekarang(k: Konteks) -> dict:
    tj = kalender.gregorian_to_javanese(k.sekarang.date())
    return {"tahun": str(tj.tahun), "nama_tahun": tj.nama_tahun}


def windu_sekarang(k: Konteks) -> dict:
    tj = kalender.gregorian_to_javanese(k.sekarang.date())
    return {"tahun": str(tj.tahun), "nama_tahun": tj.nama_tahun, "windu": tj.windu or "-"}


# --- Pencarian tabel (sudah aktif) -------------------------------------------

def neptu(k: Konteks) -> dict:
    hari = cari_hari(k.pesan)
    pasaran = cari_pasaran(k.pesan)
    if hari and pasaran:
        total = NEPTU_HARI[hari[0]] + NEPTU_PASARAN[pasaran[0]]
        return {"hasil": (f"Neptu weton {hari[0]} {pasaran[0]} adalah {total} "
                          f"({hari[0]} {NEPTU_HARI[hari[0]]} + {pasaran[0]} {NEPTU_PASARAN[pasaran[0]]}).")}
    if hari:
        return {"hasil": f"Nilai neptu hari {hari[0]} adalah {NEPTU_HARI[hari[0]]}."}
    if pasaran:
        return {"hasil": f"Nilai neptu pasaran {pasaran[0]} adalah {NEPTU_PASARAN[pasaran[0]]}."}
    hari_txt = ", ".join(f"{h} {n}" for h, n in NEPTU_HARI.items())
    pas_txt = ", ".join(f"{p} {n}" for p, n in NEPTU_PASARAN.items())
    return {"hasil": f"Sebutkan hari atau pasarannya. Neptu hari: {hari_txt}. Neptu pasaran: {pas_txt}."}


def wuku_detail(k: Konteks) -> dict:
    ditemukan = cari_wuku(k.pesan)
    if not ditemukan:
        raise PerluInfo("Wuku apa yang ingin Anda ketahui? Contoh: Wuku Sinta, "
                        "Wuku Landep, atau Wuku Watugunung.")
    w = ditemukan[0]
    urut = WUKU.index(w) + 1
    catatan = ""
    if urut == 1:
        catatan = " Wuku ini membuka siklus Pawukon."
    elif urut == len(WUKU):
        catatan = " Wuku ini menutup siklus Pawukon, setelahnya kembali ke Sinta."
    sebelum = WUKU[urut - 2] if urut > 1 else None
    sesudah = WUKU[urut] if urut < len(WUKU) else None
    urutan = ""
    if sebelum and sesudah:
        urutan = f" Didahului Wuku {sebelum} dan disusul Wuku {sesudah}."
    return {"wuku": w, "urut": str(urut),
            "hasil": f"Wuku {w} adalah wuku ke-{urut} dari 30 wuku dalam Pawukon; "
                     f"satu wuku berlangsung 7 hari.{catatan}{urutan}"}


def urutan_bulan(k: Konteks) -> dict:
    # "Setelah Besar" -> "bulan Besar", supaya kata umum (besar, pasa) dikenali.
    ditemukan = cari_bulan_jawa(k.pesan) or cari_bulan_jawa(
        re.sub(r"\b(setelah|sesudah|sebelum)\b", "bulan", k.pesan, flags=re.I))
    if not ditemukan:
        raise PerluInfo("Bulan Jawa apa yang Anda maksud? Contoh: Mulud, Ruwah, atau Besar.")
    i = BULAN_JAWA.index(ditemukan[0])
    kata = k.pesan.lower()
    if "sebelum" in kata or "mendahului" in kata:
        j = (i - 1) % 12
        return {"hasil": f"Bulan sebelum {BULAN_JAWA[i]} adalah {BULAN_JAWA[j]}."}
    j = (i + 1) % 12
    return {"hasil": f"Bulan setelah {BULAN_JAWA[i]} adalah {BULAN_JAWA[j]}."}


def ulangi_jawaban(k: Konteks) -> dict:
    if not k.terakhir:
        raise PerluInfo("Belum ada jawaban sebelumnya yang bisa diulang. "
                        "Silakan ajukan pertanyaan terlebih dahulu.")
    return {"respons_terakhir": k.terakhir}


HANDLERS = {
    "gregorian_to_javanese": gregorian_to_javanese,
    "javanese_to_gregorian": javanese_to_gregorian,
    "gregorian_to_weton": gregorian_to_weton,
    "javanese_to_weton": javanese_to_weton,
    "gregorian_to_wuku": gregorian_to_wuku,
    "tanggal_jawa_hari_ini": tanggal_jawa_hari_ini,
    "konversi_rentang": konversi_rentang,
    "selisih_tanggal": selisih_tanggal,
    "bulan_jawa_sekarang": bulan_jawa_sekarang,
    "konversi_bulan": konversi_bulan,
    "tahun_jawa_sekarang": tahun_jawa_sekarang,
    "windu_sekarang": windu_sekarang,
    "neptu": neptu,
    "wuku_detail": wuku_detail,
    "urutan_bulan": urutan_bulan,
    "ulangi_jawaban": ulangi_jawaban,
}
