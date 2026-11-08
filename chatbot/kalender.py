"""Modul perhitungan kalender Jawa (Sultanagungan): TEMPAT KODE ACUAN.

Dua fungsi di bawah sengaja belum diisi. Kerangka chatbot, pengenalan intent,
pengurai tanggal, dan handler sudah memanggil keduanya lewat antarmuka ini,
jadi saat kode acuan masuk cukup isi dua fungsi tersebut tanpa mengubah
bagian lain. Selama belum diisi, chatbot membalas dengan pesan
"perhitungan belum aktif" (lihat chatbot/handlers.py).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .kalender_data import NEPTU_HARI, NEPTU_PASARAN, BULAN_JAWA


class KalenderBelumTersedia(NotImplementedError):
    """Dilempar selama perhitungan konversi belum diisi."""


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
    windu: str = ""     # nama windu: "Adi", "Kuntara", "Sengara", "Sancaya"
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
        """Contoh: 'Jumat Legi, 1 Sura 1959 (tahun Alip)'."""
        return (f"{self.weton}, {self.tanggal} {self.nama_bulan} {self.tahun} "
                f"(tahun {self.nama_tahun})")


def gregorian_to_javanese(tgl: date) -> TanggalJawa:
    """Ubah tanggal Masehi menjadi TanggalJawa.

    TODO: isi dengan kode acuan.
    """
    raise KalenderBelumTersedia("gregorian_to_javanese belum diisi")


def javanese_to_gregorian(tanggal: int, bulan: int, tahun: int) -> date:
    """Ubah tanggal Jawa (bulan 1..12) menjadi tanggal Masehi.

    TODO: isi dengan kode acuan.
    """
    raise KalenderBelumTersedia("javanese_to_gregorian belum diisi")
