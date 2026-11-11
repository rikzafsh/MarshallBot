"""Data konstan kalender Jawa Mataraman (Sultanagungan).

Hanya berisi tabel dan nama, tanpa perhitungan. Tabel ini dipakai bersama oleh
pengurai tanggal (extractor.py), handler (handlers.py), dan modul perhitungan
(kalender.py) yang nanti diisi dari kode acuan.
"""

# --- Dina pitu (hari) --------------------------------------------------------
# Urutan mengikuti date.weekday() Python: 0 = Senin ... 6 = Minggu.
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
NEPTU_HARI = {"Minggu": 5, "Senin": 4, "Selasa": 3, "Rabu": 7,
              "Kamis": 8, "Jumat": 6, "Sabtu": 9}

HARI_ALIAS = {
    "minggu": "Minggu", "ahad": "Minggu", "ngahad": "Minggu", "radite": "Minggu",
    "senin": "Senin", "senen": "Senin", "soma": "Senin",
    "selasa": "Selasa", "anggara": "Selasa",
    "rabu": "Rabu", "rebo": "Rabu", "buda": "Rabu",
    "kamis": "Kamis", "kemis": "Kamis", "respati": "Kamis",
    "jumat": "Jumat", "jumuwah": "Jumat", "jemuwah": "Jumat", "sukra": "Jumat",
    "sabtu": "Sabtu", "setu": "Sabtu", "tumpak": "Sabtu",
}

# --- Pancawara (pasaran) -----------------------------------------------------
PASARAN = ["Legi", "Pahing", "Pon", "Wage", "Kliwon"]
NEPTU_PASARAN = {"Legi": 5, "Pahing": 9, "Pon": 7, "Wage": 4, "Kliwon": 8}
PASARAN_ALIAS = {"legi": "Legi", "manis": "Legi", "pahing": "Pahing", "pon": "Pon",
                 "wage": "Wage", "kliwon": "Kliwon"}
# Mancapat-kalima pancer: arah mata angin tiap pasaran.
PASARAN_ARAH = {"Legi": "timur", "Pahing": "selatan", "Pon": "barat",
                "Wage": "utara", "Kliwon": "tengah"}

# --- Wulan (bulan Jawa) ------------------------------------------------------
# Ejaan mengikuti dokumen rancangan MarshallBot.
BULAN_JAWA = ["Sura", "Sapar", "Mulud", "Bakdamulud", "Jumadilawal",
              "Jumadilakhir", "Rejeb", "Ruwah", "Pasa", "Sawal",
              "Dulkangidah", "Besar"]
# Bulan ganjil 30 hari, genap 29 hari; Besar 30 hari pada tahun wuntu.
HARI_BULAN_JAWA = [30, 29, 30, 29, 30, 29, 30, 29, 30, 29, 30, 29]

# Kunci alias: huruf kecil tanpa spasi atau tanda baca.
BULAN_JAWA_ALIAS = {
    "sura": "Sura", "suro": "Sura",
    "sapar": "Sapar", "safar": "Sapar",
    "mulud": "Mulud", "maulud": "Mulud",
    "bakdamulud": "Bakdamulud", "bakdomulud": "Bakdamulud",
    "jumadilawal": "Jumadilawal", "jumadilawwal": "Jumadilawal",
    "jumadilakhir": "Jumadilakhir", "jumadilakir": "Jumadilakhir",
    "rejeb": "Rejeb", "rajab": "Rejeb",
    "ruwah": "Ruwah", "syakban": "Ruwah",
    "pasa": "Pasa", "poso": "Pasa",
    "sawal": "Sawal", "syawal": "Sawal",
    "dulkangidah": "Dulkangidah", "dulkaidah": "Dulkangidah",
    "zulkaidah": "Dulkangidah", "sela": "Dulkangidah", "selo": "Dulkangidah",
    "besar": "Besar", "dulhijjah": "Besar", "zulhijah": "Besar",
}
# Alias yang juga kata umum bahasa Indonesia. Kata ini hanya dianggap nama bulan
# bila diawali angka tanggal ("10 Besar") atau didahului kata "bulan".
BULAN_JAWA_KATA_UMUM = {"besar", "pasa", "sela", "selo"}

# --- Bulan Masehi ------------------------------------------------------------
BULAN_MASEHI = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
                "Agustus", "September", "Oktober", "November", "Desember"]
BULAN_MASEHI_ALIAS = {
    "januari": 1, "jan": 1, "februari": 2, "pebruari": 2, "feb": 2, "peb": 2,
    "maret": 3, "mar": 3, "april": 4, "apr": 4, "mei": 5, "juni": 6, "jun": 6,
    "juli": 7, "jul": 7, "agustus": 8, "agu": 8, "agt": 8, "ags": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9, "oktober": 10, "okt": 10, "november": 11,
    "nov": 11, "nopember": 11, "desember": 12, "des": 12,
}

# --- Tahun Jawa dan windu ----------------------------------------------------
WINDU_TAHUN = ["Alip", "Ehe", "Jimawal", "Je", "Dal", "Be", "Wawu", "Jimakir"]
WINDU_NAMA = ["Adi", "Kuntara", "Sengara", "Sancaya"]  # 4 windu = 32 tahun

# --- Pawukon: 30 wuku, masing-masing 7 hari (siklus 210 hari) ------------------
WUKU = ["Sinta", "Landep", "Wukir", "Kurantil", "Tolu", "Gumbreg", "Warigalit",
        "Warigagung", "Julungwangi", "Sungsang", "Galungan", "Kuningan",
        "Langkir", "Mandasiya", "Julungpujud", "Pahang", "Kuruwelut", "Marakeh",
        "Tambir", "Medangkungan", "Maktal", "Wuye", "Manahil", "Prangbakat",
        "Bala", "Wugu", "Wayang", "Kulawu", "Dukut", "Watugunung"]
WUKU_ALIAS = {"mandhasiya": "Mandasiya", "gumreg": "Gumbreg"}


def kunci(teks: str) -> str:
    """Bentuk kunci pencarian: huruf kecil, tanpa spasi atau tanda baca."""
    return "".join(c for c in teks.lower() if c.isalnum())


WUKU_KUNCI = {**{kunci(n): n for n in WUKU}, **WUKU_ALIAS}
BULAN_JAWA_KUNCI = {**{kunci(n): n for n in BULAN_JAWA}, **BULAN_JAWA_ALIAS}
