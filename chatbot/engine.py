"""Mesin chatbot berbasis aturan: praproses, skor kemiripan, keputusan, jawaban.

Alur (sama dengan materi praktikum):
    pesan -> preprocess -> similarity ke setiap pola -> ambil tertinggi
          -> skor >= ambang ? respons intent : fallback

Tambahan untuk MarshallBot:
- tanggal dalam pesan diganti token seragam sebelum dibandingkan (extractor.py);
- intent bertanda "handler" menghasilkan jawaban dinamis lewat fungsi handler,
  sedangkan intent tanpa handler memakai jawaban statis dari file tema.
"""
from __future__ import annotations

import random
import re
from datetime import datetime
from difflib import SequenceMatcher

from .extractor import mask_entitas
from .kalender_data import (
    BULAN_JAWA_KATA_UMUM, BULAN_JAWA_KUNCI, HARI_ALIAS, PASARAN_ALIAS, WUKU_KUNCI,
)

DEFAULT_THRESHOLD = 0.45
BOBOT_JACCARD, BOBOT_FUZZY, BOBOT_CAKUPAN = 0.4, 0.3, 0.3

# Kata tidak baku -> baku. Tambahkan sesuai kebutuhan tema.
NORMALISASI = {
    "gmn": "bagaimana", "gimana": "bagaimana", "gmna": "bagaimana",
    "bgmn": "bagaimana", "bagaimanakah": "bagaimana",
    "brp": "berapa", "berapakah": "berapa", "brapa": "berapa",
    "tgl": "tanggal", "tanggalnya": "tanggal", "tangal": "tanggal",
    "kpn": "kapan", "kapankah": "kapan", "dmn": "dimana", "dimanakah": "dimana",
    "yg": "yang", "utk": "untuk", "dgn": "dengan", "dg": "dengan", "krn": "karena",
    "jg": "juga", "sm": "sama", "aja": "saja", "ga": "tidak", "gak": "tidak",
    "nggak": "tidak", "tdk": "tidak", "apakah": "apa", "siapakah": "siapa",
    "hr": "hari", "bln": "bulan", "thn": "tahun", "msh": "masehi",
    "masehi": "masehi", "gregorian": "masehi", "hijriyah": "hijriah",
    "penanggalan": "kalender", "almanak": "kalender", "tarikh": "kalender",
    "puasa": "pasa", "poso": "pasa", "suro": "sura", "rajab": "rejeb",
    "jumuwah": "jumat", "jemuwah": "jumat", "senen": "senin", "rebo": "rabu",
    "kemis": "kamis", "setu": "sabtu", "ahad": "minggu",
    "makasih": "terima", "thanks": "terima", "thx": "terima", "suwun": "nuwun",
    "hi": "halo", "hai": "halo", "hello": "halo", "hallo": "halo", "hay": "halo",
    "konversikan": "konversi", "mengonversi": "konversi", "ubah": "konversi",
    "ubahlah": "konversi", "terjemahkan": "konversi", "tampilkan": "daftar",
    "sebutkan": "daftar", "sebut": "daftar", "sebutin": "daftar",
    "jatuhnya": "jatuh", "bertepatan": "jatuh",
    "bakda": "bakda", "dulhijjah": "besar",
}

# Frasa -> kata tunggal, diterapkan sebelum pemecahan kata.
FRASA = {
    "hari ini": "sekarang", "saat ini": "sekarang", "kali ini": "sekarang",
    "tahun ini": "sekarang", "bulan ini": "sekarang",
    "terima kasih": "terima nuwun", "matur nuwun": "terima nuwun",
    "sampai jumpa": "dadah", "selamat tinggal": "dadah",
    "bakda mulud": "bakdamulud", "jumadil awal": "jumadilawal",
    "jumadil akhir": "jumadilakhir", "jumadilakir": "jumadilakhir",
}

STOPWORDS = {
    "yang", "di", "ke", "dari", "dan", "atau", "itu", "ini", "apa", "mau", "ingin",
    "saya", "aku", "kak", "kakak", "mas", "mbak", "dong", "deh", "sih", "ya", "nih",
    "tolong", "mohon", "bisa", "dengan", "untuk", "pada", "adalah", "ialah", "dalam",
    "lah", "kah", "tuh", "sebenarnya", "coba", "kalau", "jika", "maka", "oleh",
    "sebuah", "suatu", "para", "si", "sang", "kok", "lho", "nya", "ada",
}

_SUFIKS_NYA = re.compile(r"^(.{4,})nya$")

# Nama hari, pasaran, bulan, dan wuku diganti token jenisnya, supaya
# "neptu Jumat Kliwon" cocok dengan pola "neptu Rabu Pahing".
TOKEN_HARI, TOKEN_PASARAN = "namahari", "namapasaran"
TOKEN_BULAN, TOKEN_WUKU = "namabulan", "namawuku"


def _jenis_nama(kata: str, sebelumnya: str | None) -> str | None:
    if kata in HARI_ALIAS:
        return TOKEN_HARI
    if kata in PASARAN_ALIAS:
        return TOKEN_PASARAN
    if kata in BULAN_JAWA_KUNCI:
        # Kata umum (besar, pasa) hanya dianggap nama bulan setelah kata "bulan".
        if kata in BULAN_JAWA_KATA_UMUM and sebelumnya != "bulan":
            return None
        return TOKEN_BULAN
    if kata in WUKU_KUNCI and sebelumnya == "wuku":
        return TOKEN_WUKU
    return None


def preprocess(teks: str) -> list[str]:
    """Teks mentah -> daftar token seragam."""
    teks = mask_entitas(teks).lower()
    teks = re.sub(r"[^a-z0-9\s]", " ", teks)
    teks = re.sub(r"\s+", " ", teks).strip()
    for asal, baku in FRASA.items():
        teks = re.sub(rf"\b{re.escape(asal)}\b", baku, teks)
    tokens: list[str] = []
    for kata in teks.split():
        m = _SUFIKS_NYA.match(kata)
        if m and kata not in NORMALISASI:      # wetonnya -> weton, pasarannya -> pasaran
            kata = m.group(1)
        for k in NORMALISASI.get(kata, kata).split():
            if k and k not in STOPWORDS:
                tokens.append(_jenis_nama(k, tokens[-1] if tokens else None) or k)
    return tokens


def similarity(a: list[str], b: list[str]) -> float:
    """Skor 0..1 = 0,4 Jaccard + 0,3 Fuzzy + 0,3 Cakupan."""
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    jaccard = len(sa & sb) / len(sa | sb)
    fuzzy = SequenceMatcher(None, " ".join(a), " ".join(b)).ratio()
    cakupan = len(sb & sa) / len(sb)
    return BOBOT_JACCARD * jaccard + BOBOT_FUZZY * fuzzy + BOBOT_CAKUPAN * cakupan


# --- Validasi tema -----------------------------------------------------------

def validate_theme(theme: dict) -> list[str]:
    """Kembalikan daftar kesalahan; kosong berarti tema valid."""
    err: list[str] = []
    for kunci in ("id", "bot_name", "title", "fallback", "intents"):
        if kunci not in theme:
            err.append(f"Kunci '{kunci}' tidak ada")
    if err:
        return err
    if not theme["fallback"]:
        err.append("fallback minimal 1 kalimat")
    tags: set[str] = set()
    for i in theme["intents"]:
        tag = i.get("tag", "(tanpa tag)")
        if tag in tags:
            err.append(f"Tag ganda: {tag}")
        tags.add(tag)
        if not i.get("patterns"):
            err.append(f"Intent '{tag}' tidak punya pola")
        if not i.get("responses"):
            err.append(f"Intent '{tag}' tidak punya respons")
    return err


# --- Mesin -------------------------------------------------------------------

class PerluInfo(Exception):
    """Handler butuh data tambahan dari pengguna; isi pesan = pertanyaan balik."""


class Konteks:
    """Bahan yang diterima handler dari mesin."""

    def __init__(self, pesan: str, intent: dict, terakhir: str | None, sekarang: datetime):
        self.pesan = pesan
        self.intent = intent
        self.terakhir = terakhir      # balasan bot sebelumnya (untuk "ulangi")
        self.sekarang = sekarang


class ChatbotEngine:
    def __init__(self, theme: dict, threshold: float = DEFAULT_THRESHOLD, handlers: dict | None = None):
        errors = validate_theme(theme)
        if errors:
            raise ValueError(f"Tema '{theme.get('id', '?')}' tidak valid: " + "; ".join(errors))
        self.theme = theme
        self.threshold = threshold
        self.handlers = handlers or {}
        self._intents = {i["tag"]: i for i in theme["intents"]}
        self._responses = {i["tag"]: i["responses"] for i in theme["intents"]}
        # (tag, pola asli, token pola) untuk setiap pola, dihitung sekali.
        self._patterns = [(i["tag"], p, preprocess(p))
                          for i in theme["intents"] for p in i["patterns"]]

    # 1 + 2: memahami dan memutuskan
    def scores(self, pesan: str) -> list[dict]:
        """Skor terbaik setiap intent, diurutkan dari tertinggi."""
        tokens = preprocess(pesan)
        terbaik: dict[str, tuple[float, str]] = {}
        for tag, pola, tok in self._patterns:
            s = similarity(tokens, tok)
            if tag not in terbaik or s > terbaik[tag][0]:
                terbaik[tag] = (s, pola)
        hasil = [{"intent": t, "score": round(s, 4), "pattern": p} for t, (s, p) in terbaik.items()]
        return sorted(hasil, key=lambda x: x["score"], reverse=True)

    def classify(self, pesan: str) -> tuple[str | None, float]:
        urut = self.scores(pesan)
        if not urut:
            return None, 0.0
        atas = urut[0]
        if atas["score"] < self.threshold:
            return None, atas["score"]
        return atas["intent"], atas["score"]

    def explain(self, pesan: str, n: int = 3) -> list[dict]:
        """Tiga kandidat teratas, untuk mode belajar."""
        hasil = self.scores(pesan)[:n]
        for h in hasil:
            h["above_threshold"] = h["score"] >= self.threshold
        return hasil

    # 3: menjawab
    def reply(self, pesan: str, terakhir: str | None = None, sekarang: datetime | None = None) -> dict:
        sekarang = sekarang or datetime.now()
        tag, skor = self.classify(pesan)
        status = "ok"
        isian: dict[str, str] = {}
        if tag is None:
            teks = random.choice(self.theme["fallback"])
        else:
            intent = self._intents[tag]
            teks = random.choice(self._responses[tag])
            nama_handler = intent.get("handler")
            if nama_handler:
                fn = self.handlers.get(nama_handler)
                if fn is None:
                    status = "handler_hilang"
                    teks = self.theme.get("pesan_tidak_aktif", teks)
                else:
                    teks, isian, status = self._jalankan(fn, intent, teks, pesan, terakhir, sekarang)
        return {"reply": self._isi_placeholder(teks, isian), "intent": tag,
                "score": round(skor, 4), "status": status}

    def _jalankan(self, fn, intent, template, pesan, terakhir, sekarang):
        from .kalender import KalenderBelumTersedia
        try:
            isian = fn(Konteks(pesan, intent, terakhir, sekarang)) or {}
            return template, isian, "ok"
        except PerluInfo as e:
            return str(e), {}, "perlu_info"
        except KalenderBelumTersedia:
            pesan_nonaktif = self.theme.get(
                "pesan_tidak_aktif",
                "Perhitungan kalender untuk permintaan ini belum diaktifkan.")
            return pesan_nonaktif, {}, "perhitungan_belum_aktif"

    def isi(self, teks: str) -> str:
        """Isi placeholder umum ({waktu}, {tanggal}, {nama_bot}, {salam_jawa})."""
        return self._isi_placeholder(teks, {})

    def _isi_placeholder(self, teks: str, tambahan: dict[str, str]) -> str:
        sekarang = datetime.now()
        nilai = {
            "waktu": sekarang.strftime("%H:%M"),
            "tanggal": sekarang.strftime("%d-%m-%Y"),
            "nama_bot": self.theme["bot_name"],
            "salam_jawa": salam_jawa(sekarang.hour),
            **{k: str(v) for k, v in tambahan.items()},
        }
        return re.sub(r"\{(\w+)\}", lambda m: nilai.get(m.group(1), m.group(0)), teks)


def salam_jawa(jam: int) -> str:
    """Sugeng enjing (pagi), siyang, sonten, atau dalu menurut jam."""
    if 3 <= jam < 11:
        return "Sugeng enjing"
    if 11 <= jam < 15:
        return "Sugeng siyang"
    if 15 <= jam < 18:
        return "Sugeng sonten"
    return "Sugeng dalu"
