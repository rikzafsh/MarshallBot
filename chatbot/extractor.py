"""Mengenali tanggal dan nama dalam kalimat pengguna.

Dua kegunaan:
1. mask_entitas(): tanggal diganti token seragam (tglmasehi, tgljawa,
   tglrentang) sebelum dibandingkan dengan pola. Dengan begitu
   "weton 17 Agustus 1945" dan "weton 3 Mei 2001" memiliki bentuk sama.
2. analisis(): mengambil nilai tanggalnya untuk dipakai handler.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from .kalender_data import (
    BULAN_JAWA, BULAN_JAWA_KATA_UMUM, BULAN_JAWA_KUNCI, BULAN_MASEHI,
    BULAN_MASEHI_ALIAS, HARI_ALIAS, PASARAN_ALIAS, WUKU_KUNCI, kunci,
)

TOKEN_MASEHI = "tglmasehi"
TOKEN_JAWA = "tgljawa"
TOKEN_RENTANG = "tglrentang"


def _alternasi(kata):
    return "|".join(sorted((re.escape(k) for k in kata), key=len, reverse=True))


_M_MASEHI = _alternasi(BULAN_MASEHI_ALIAS)
_M_JAWA = _alternasi(
    k for k in BULAN_JAWA_KUNCI if k.isalpha()) + r"|bakda\s+mulud|jumadil\s+awal|jumadil\s+akhir"

_POLA = re.compile(
    rf"""
    (?<!\d)(?:
        (?P<r_a>\d{{1,2}})\s*(?:sampai|hingga|s\.?\s?d\.?|-|–)\s*(?P<r_b>\d{{1,2}})
            \s+(?P<r_m>{_M_MASEHI})\s+(?P<r_y>\d{{4}})
      | (?P<n_d>\d{{1,2}})\s*[/\-.]\s*(?P<n_m>\d{{1,2}})\s*[/\-.]\s*(?P<n_y>\d{{4}})
      | (?P<m_d>\d{{1,2}})\s+(?P<m_n>{_M_MASEHI})\s+(?:tahun\s+)?(?P<m_y>\d{{4}})
      | (?P<j_d>\d{{1,2}})\s+(?P<j_n>{_M_JAWA})(?:\s+(?:tahun\s+)?(?P<j_y>\d{{4}}))?
    )(?![\d\w])
    """,
    re.IGNORECASE | re.VERBOSE,
)

RELATIF = {"hari ini": 0, "saat ini": 0, "sekarang": 0, "kini": 0,
           "besok": 1, "esok": 1, "lusa": 2, "kemarin": -1}
_POLA_RELATIF = re.compile(
    r"\b(hari ini|saat ini|sekarang|kini|besok|esok|lusa|kemarin)\b", re.I)


@dataclass
class TglJawa:
    tanggal: int
    bulan: int            # 1..12
    tahun: int | None = None

    def teks(self) -> str:
        t = f"{self.tanggal} {BULAN_JAWA[self.bulan - 1]}"
        return f"{t} {self.tahun}" if self.tahun else t


@dataclass
class Entitas:
    masked: str = ""
    masehi: list[date] = field(default_factory=list)
    jawa: list[TglJawa] = field(default_factory=list)
    rentang: tuple[date, date] | None = None
    urutan: list[tuple[str, object]] = field(default_factory=list)  # urutan kemunculan
    salah: list[str] = field(default_factory=list)                  # tanggal tak valid
    relatif: int | None = None   # selisih hari dari hari ini: 0, 1, 2, -1


def format_tanggal(d: date) -> str:
    return f"{d.day} {BULAN_MASEHI[d.month - 1]} {d.year}"


def _bulan_jawa(teks: str) -> int | None:
    nama = BULAN_JAWA_KUNCI.get(kunci(teks))
    return BULAN_JAWA.index(nama) + 1 if nama else None


def analisis(teks: str) -> Entitas:
    """Kenali semua tanggal dalam teks dan hasilkan versi bertoken."""
    ent = Entitas()

    def ganti(m: re.Match) -> str:
        g = m.groupdict()
        mentah = m.group(0).strip()
        try:
            if g["r_a"]:
                bln = BULAN_MASEHI_ALIAS[g["r_m"].lower()]
                th = int(g["r_y"])
                awal, akhir = date(th, bln, int(g["r_a"])), date(th, bln, int(g["r_b"]))
                if akhir < awal:
                    raise ValueError
                ent.rentang = (awal, akhir)
                ent.urutan.append(("rentang", ent.rentang))
                return f" {TOKEN_RENTANG} "
            if g["n_d"]:
                d = date(int(g["n_y"]), int(g["n_m"]), int(g["n_d"]))
                ent.masehi.append(d)
                ent.urutan.append(("masehi", d))
                return f" {TOKEN_MASEHI} "
            if g["m_d"]:
                d = date(int(g["m_y"]), BULAN_MASEHI_ALIAS[g["m_n"].lower()], int(g["m_d"]))
                ent.masehi.append(d)
                ent.urutan.append(("masehi", d))
                return f" {TOKEN_MASEHI} "
        except ValueError:
            ent.salah.append(mentah)
            return f" {TOKEN_RENTANG if g['r_a'] else TOKEN_MASEHI} "

        # Tanggal Jawa. Nama bulan yang juga kata umum (besar, pasa) hanya sah
        # bila ada angka tanggal di depannya; itu sudah dijamin oleh pola.
        bln = _bulan_jawa(re.sub(r"\s+", "", g["j_n"]))
        hari = int(g["j_d"])
        if bln is None or not 1 <= hari <= 30:
            ent.salah.append(mentah)
            return f" {TOKEN_JAWA} "
        tj = TglJawa(hari, bln, int(g["j_y"]) if g["j_y"] else None)
        ent.jawa.append(tj)
        ent.urutan.append(("jawa", tj))
        return f" {TOKEN_JAWA} "

    ent.masked = re.sub(r"\s+", " ", _POLA.sub(ganti, teks)).strip()
    rel = _POLA_RELATIF.search(teks)
    if rel:
        ent.relatif = RELATIF[rel.group(1).lower()]
    return ent


def mask_entitas(teks: str) -> str:
    return analisis(teks).masked


# --- Pencarian nama (hari, pasaran, wuku, bulan) -----------------------------

def _kandidat(teks: str) -> list[str]:
    """Kata tunggal dan pasangan kata berurutan, sebagai kunci."""
    kata = re.findall(r"[a-zA-Z]+", teks.lower())
    pasangan = [kata[i] + kata[i + 1] for i in range(len(kata) - 1)]
    return kata + pasangan


def cari_nama(teks: str, kamus: dict[str, str], umum: set[str] | None = None) -> list[str]:
    """Cari semua nama dalam kamus (berurutan, tanpa duplikat).

    `umum` berisi kunci yang juga kata biasa; kunci itu hanya diterima bila
    didahului kata "bulan", "wuku", atau "hari".
    """
    hasil: list[str] = []
    kata = re.findall(r"[a-zA-Z]+", teks.lower())
    for i, k in enumerate(kata):
        for kand, lebar in ((k, 1), (k + kata[i + 1], 2) if i + 1 < len(kata) else (None, 0)):
            if kand is None or kand not in kamus:
                continue
            if umum and kand in umum and (i == 0 or kata[i - 1] not in {"bulan", "wuku", "hari"}):
                continue
            nama = kamus[kand]
            if nama not in hasil:
                hasil.append(nama)
    return hasil


def cari_hari(teks: str) -> list[str]:
    return cari_nama(teks, HARI_ALIAS)


def cari_pasaran(teks: str) -> list[str]:
    return cari_nama(teks, PASARAN_ALIAS)


def cari_wuku(teks: str) -> list[str]:
    return cari_nama(teks, WUKU_KUNCI)


def cari_bulan_jawa(teks: str) -> list[str]:
    return cari_nama(teks, BULAN_JAWA_KUNCI, umum=BULAN_JAWA_KATA_UMUM)
