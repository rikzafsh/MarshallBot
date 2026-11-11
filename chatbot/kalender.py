"""Perhitungan kalender Jawa Mataraman (Sultanagungan).

Port dari kode acuan `farcode.js` (fungsi greg2JD, jd2greg, jd2np, jd2jawa,
jawa2jd, dan turunannya). Rumus dan konstanta dipertahankan apa adanya
supaya hasilnya sama dengan kode acuan; hanya pembulatan yang disesuaikan:

* Math.round JavaScript membulatkan .5 ke atas, sedangkan round() Python
  membulatkan ke genap. Karena itu dipakai js_round() di bawah.
* Dina berganti pada tengah malam (jd2midnight), seperti pada kode acuan.

Antarmuka yang dipakai chatbot (chatbot/handlers.py):
    gregorian_to_javanese(date)                  -> TanggalJawa
    javanese_to_gregorian(tanggal, bulan, tahun) -> date
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

from .kalender_data import (
    BULAN_JAWA, NEPTU_HARI, NEPTU_PASARAN, PASARAN, WINDU_NAMA, WINDU_TAHUN, WUKU,
)

# Urutan saptawara pada kode acuan: 1 = Ahad (Minggu) ... 7 = Sabtu.
_SAPTAWARA = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"]

# Konstanta kalender Jawa (farcode.js, bagian "KALENDER JAWA").
AMBAL_JAWA = 2587
AMBAL_TAHUN = AMBAL_JAWA - 427                      # 2160 tahun
AMBAL_KURUP = AMBAL_TAHUN // 120                    # 18 kurup
AMBAL_HARI = (AMBAL_TAHUN // 120) * 42524 + 1       # 765433 hari
HARI_KURUP = 42524                                  # 15 windu kurang 1 hari
HARI_WINDU = 2835                                   # 81 selapan
EPOCH_JD = 1917963.5


class TanggalTidakValid(ValueError):
    """Tanggal Jawa yang tidak pernah ada (mis. 30 Sapar)."""


class KalenderBelumTersedia(NotImplementedError):
    """Cadangan bila perhitungan dinonaktifkan; tidak dilempar oleh modul ini."""


def js_round(x: float) -> int:
    """Math.round JavaScript: .5 dibulatkan ke atas."""
    return math.floor(x + 0.5)


# --- Julian Date ---------------------------------------------------------------

def greg2jd(tahun: int, bulan: int, tanggal: int) -> float:
    if bulan <= 2:
        tahun -= 1
        bulan += 12
    a = tahun // 100
    b = 2 - a + a // 4
    return (math.floor(365.25 * (tahun + 4716)) + math.floor(30.6001 * (bulan + 1))
            + tanggal + b - 1524.5)


def jd2greg(jd: float) -> tuple[int, int, int]:
    z = math.floor(jd + 0.5)
    f = jd + 0.5 - z
    a = z
    if z >= 2299161:
        alpha = math.floor((z - 1867216.25) / 36524.25)
        a += 1 + alpha - alpha // 4
    b = a + 1524
    c = math.floor((b - 122.1) / 365.25)
    d = math.floor(365.25 * c)
    e = math.floor((b - d) / 30.6001)
    hari = math.floor(b - d - math.floor(30.6001 * e) + f)
    bulan = e - 1 if e < 14 else e - 13
    tahun = c - 4716 if bulan > 2 else c - 4715
    return tahun, bulan, hari


def jd2midnight(jd: float) -> float:
    return math.floor(jd + 0.5) - 0.5


# --- Pawukon (siklus 210 hari) ---------------------------------------------------

def jd2np(jd: float) -> int:
    """Nomor Pawukon 1..210."""
    return int((jd2midnight(jd) + 64.5) % 210) + 1


def np2wuku(np: int) -> int:
    return (np - 1) // 7 + 1


def np2w7(np: int) -> int:
    return (np - 1) % 7 + 1


def np2w5(np: int) -> int:
    return np % 5 + 1


# --- Kalender Jawa ----------------------------------------------------------------

def jd2jawa(jd: float) -> tuple[int, int, int]:
    """Julian Date -> (tahun, bulan 1..12, tanggal) Jawa."""
    a = int(jd2midnight(jd) - EPOCH_JD)
    b = a // AMBAL_HARI
    c = a - b * AMBAL_HARI
    d = c // HARI_KURUP - c // (HARI_KURUP * AMBAL_KURUP)
    e = c - d * HARI_KURUP
    f = e // HARI_WINDU
    g = e - HARI_WINDU * f
    h = math.floor((g - g // 2834) / 354.36667 + 0.0013)
    i = g - js_round(h * 354.36667)
    j = math.floor((i - i // 354) / 29.5)
    tanggal = i - js_round(j * 29.5) + 1
    tahun = b * AMBAL_TAHUN + d * 120 + f * 8 + h + 427
    return tahun, j + 1, tanggal


def jawa2jd(tanggal: int, bulan: int, tahun: int) -> float:
    """(tanggal, bulan 1..12, tahun) Jawa -> Julian Date tengah malam."""
    ambal_hari, ambal_thn = 765433, 2160
    t = tahun - 427
    a = t // ambal_thn
    b = (t - a * ambal_thn) // 120
    c = (t - (a * ambal_thn + b * 120)) // 8
    d = t - a * ambal_thn - b * 120 - c * 8
    e = bulan - 1
    return (1917962.5 + a * ambal_hari + b * 42524 + c * 2835
            + js_round(d * 354.35) + js_round(e * 29.5) + tanggal)


def nomor_tahun_dalam_windu(tahun: int) -> int:
    """1 = Alip ... 8 = Jimakir."""
    return (tahun - 3) % 8 + 1


def nomor_windu4(tahun: int) -> int:
    """1 = Adi, 2 = Kuntara, 3 = Sengara, 4 = Sancaya."""
    return ((tahun - 75) // 8) % 4 + 1


def panjang_tahun(tahun: int) -> int:
    """354 (wastu) atau 355 (wuntu) hari."""
    return int(jawa2jd(1, 1, tahun + 1) - jawa2jd(1, 1, tahun))


# --- Antarmuka untuk chatbot ------------------------------------------------------

@dataclass(frozen=True)
class TanggalJawa:
    """Hasil konversi satu tanggal ke kalender Jawa."""
    tanggal: int        # 1..30
    bulan: int          # 1..12 (1 = Sura)
    tahun: int          # tahun Jawa, misal 1959
    hari: str           # dina pitu, ejaan Indonesia: "Jumat"
    pasaran: str        # "Legi" ...
    wuku: str           # "Sinta" ...
    nama_tahun: str     # "Alip", "Ehe", ... (nama tahun dalam windu)
    windu: str = ""     # "Adi", "Kuntara", "Sengara", "Sancaya"
    wuntu: bool | None = None  # True = tahun wuntu (355 hari), False = wastu

    @property
    def nama_bulan(self) -> str:
        return BULAN_JAWA[self.bulan - 1]

    @property
    def weton(self) -> str:
        return f"{self.hari} {self.pasaran}"

    @property
    def neptu(self) -> int:
        return NEPTU_HARI[self.hari] + NEPTU_PASARAN[self.pasaran]

    def teks(self) -> str:
        """Contoh: 'Jumat Legi, 1 Sura 1959 (tahun Dal)'."""
        return (f"{self.weton}, {self.tanggal} {self.nama_bulan} {self.tahun} "
                f"(tahun {self.nama_tahun})")


def gregorian_to_javanese(tgl: date) -> TanggalJawa:
    """Tanggal Masehi -> TanggalJawa lengkap (weton, wuku, tahun, windu)."""
    jd = greg2jd(tgl.year, tgl.month, tgl.day)
    tahun, bulan, tanggal = jd2jawa(jd)
    np = jd2np(jd)
    return TanggalJawa(
        tanggal=tanggal, bulan=bulan, tahun=tahun,
        hari=_SAPTAWARA[np2w7(np) - 1],
        pasaran=PASARAN[np2w5(np) - 1],
        wuku=WUKU[np2wuku(np) - 1],
        nama_tahun=WINDU_TAHUN[nomor_tahun_dalam_windu(tahun) - 1],
        windu=WINDU_NAMA[nomor_windu4(tahun) - 1],
        wuntu=panjang_tahun(tahun) == 355,
    )


def panjang_bulan(bulan: int, tahun: int) -> int:
    """Jumlah hari satu bulan Jawa menurut jawa2jd (29 atau 30)."""
    if bulan == 12:
        berikut = jawa2jd(1, 1, tahun + 1)
    else:
        berikut = jawa2jd(1, bulan + 1, tahun)
    return int(berikut - jawa2jd(1, bulan, tahun))


def javanese_to_gregorian(tanggal: int, bulan: int, tahun: int) -> date:
    """Tanggal Jawa (bulan 1..12) -> tanggal Masehi, memakai jawa2jd.

    Melempar TanggalTidakValid bila tanggal itu tidak ada pada kalender
    (misalnya 30 Sapar, atau 30 Besar pada tahun wastu).

    Catatan: pada tahun Jimakir, jd2jawa (Masehi -> Jawa) dan jawa2jd
    (Jawa -> Masehi) pada kode acuan berbeda satu hari karena konstanta
    354,36667 vs 354,35. Lihat tests/test_kalender.py.
    """
    if not (1 <= bulan <= 12 and 1 <= tanggal <= 30):
        raise TanggalTidakValid(f"{tanggal} {bulan} {tahun}")
    if tanggal > panjang_bulan(bulan, tahun):
        raise TanggalTidakValid(f"{tanggal} {BULAN_JAWA[bulan - 1]} {tahun}")
    t, b, h = jd2greg(jawa2jd(tanggal, bulan, tahun))
    return date(t, b, h)
