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

import json
import random
import re
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

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
    return round(BOBOT_JACCARD * jaccard + BOBOT_FUZZY * fuzzy + BOBOT_CAKUPAN * cakupan, 4)


# --- Validasi dan pemuatan tema ---------------------------------------------

KUNCI_WAJIB_TEMA = ["id", "name", "bot_name", "avatar", "color", "description",
                    "greeting", "suggestions", "fallback", "intents"]


def validate_theme(theme: dict) -> list[str]:
    """Periksa struktur file tema. Kembalikan daftar masalah (kosong = valid)."""
    masalah = [f"kunci '{k}' tidak ada" for k in KUNCI_WAJIB_TEMA if k not in theme]
    if masalah:
        return masalah
    if not theme["fallback"]:
        masalah.append("daftar 'fallback' kosong")
    tags: set[str] = set()
    pola_milik: dict[str, str] = {}
    for i, intent in enumerate(theme["intents"]):
        for k in ("tag", "patterns", "responses"):
            if k not in intent:
                masalah.append(f"intent ke-{i + 1}: kunci '{k}' tidak ada")
        tag = intent.get("tag", f"#{i + 1}")
        if tag in tags:
            masalah.append(f"tag '{tag}' dipakai lebih dari sekali")
        tags.add(tag)
        if not intent.get("patterns"):
            masalah.append(f"intent '{tag}': patterns kosong")
        if not intent.get("responses"):
            masalah.append(f"intent '{tag}': responses kosong")
        for pola in intent.get("patterns", []):
            kunci = " ".join(preprocess(pola))
            if not kunci:
                masalah.append(f"intent '{tag}': pola '{pola}' kosong setelah praproses")
            elif kunci in pola_milik and pola_milik[kunci] != tag:
                masalah.append(f"pola '{pola}' ada di intent '{pola_milik[kunci]}' dan '{tag}'")
            pola_milik.setdefault(kunci, tag)
    return masalah


def load_themes(folder: str | Path) -> dict[str, dict]:
    """Baca semua themes/*.json dan kembalikan {id_tema: data}."""
    themes: dict[str, dict] = {}
    for path in sorted(Path(folder).glob("*.json")):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        masalah = validate_theme(data)
        if masalah:
            raise ValueError(f"File tema {path.name} tidak valid:\n- " + "\n- ".join(masalah))
        themes[data["id"]] = data
    return themes


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
        self.theme = theme
        self.threshold = threshold
        self.handlers = handlers or {}
        self._intents = {i["tag"]: i for i in theme["intents"]}
        self._responses = {i["tag"]: i["responses"] for i in theme["intents"]}
        # (tag, pola asli, token pola) untuk setiap pola, dihitung sekali.
        self._patterns = [(i["tag"], p, preprocess(p))
                          for i in theme["intents"] for p in i["patterns"]]

    # 1 + 2: memahami dan memutuskan
    def explain(self, pesan: str, top: int = 3) -> list[dict]:
        """Kandidat intent terbaik beserta pola dan skornya (untuk belajar/debug)."""
        tokens = preprocess(pesan)
        terbaik: dict[str, dict] = {}
        for tag, pola, pola_tokens in self._patterns:
            skor = similarity(tokens, pola_tokens)
            if tag not in terbaik or skor > terbaik[tag]["score"]:
                terbaik[tag] = {"intent": tag, "pattern": pola, "score": skor}
        return sorted(terbaik.values(), key=lambda x: x["score"], reverse=True)[:top]

    def classify(self, pesan: str) -> tuple[str | None, float]:
        """Kembalikan (tag_intent, skor). tag None jika di bawah ambang."""
        kandidat = self.explain(pesan, top=1)
        if not kandidat:
            return None, 0.0
        best = kandidat[0]
        if best["score"] < self.threshold:
            return None, best["score"]
        return best["intent"], best["score"]

    # 3: menjawab
    def reply(self, pesan: str, terakhir: str | None = None, sekarang: datetime | None = None) -> dict:
        if not pesan or not pesan.strip():
            return {"reply": "Pesannya masih kosong. Silakan ketik pertanyaan Anda.",
                    "intent": None, "score": 0.0, "status": "ok"}
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
                "score": skor, "status": status}

    def _jalankan(self, fn, intent, template, pesan, terakhir, sekarang):
        from .kalender import KalenderBelumTersedia, TanggalTidakValid
        try:
            isian = fn(Konteks(pesan, intent, terakhir, sekarang)) or {}
            return template, isian, "ok"
        except PerluInfo as e:
            return str(e), {}, "perlu_info"
        except TanggalTidakValid as e:
            return (f"Tanggal Jawa {e} tidak ada dalam kalender. Periksa kembali, "
                    "misalnya jumlah hari pada bulan itu."), {}, "perlu_info"
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
