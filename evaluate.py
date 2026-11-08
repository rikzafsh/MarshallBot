"""Ukur akurasi klasifikasi intent dengan kalimat uji baru.

    python evaluate.py                 # tema marshall, ambang 0,45
    python evaluate.py --sweep         # bandingkan beberapa ambang
    python evaluate.py --salah         # tampilkan hanya kalimat yang salah

Format evaluasi/<tema>.csv:  kalimat,intent   (intent 'fallback' = harus ditolak)
"""
from __future__ import annotations

import argparse
import csv
import sys

from app import BASE_DIR, load_themes
from chatbot.engine import ChatbotEngine, DEFAULT_THRESHOLD

SWEEP = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.70]


def baca_csv(path) -> list[tuple[str, str]]:
    with open(path, encoding="utf-8", newline="") as f:
        return [(r["kalimat"].strip(), r["intent"].strip()) for r in csv.DictReader(f)]


def nilai(engine: ChatbotEngine, data) -> tuple[float, list]:
    salah = []
    for kalimat, harapan in data:
        tag, skor = engine.classify(kalimat)
        tebakan = tag or "fallback"
        if tebakan != harapan:
            salah.append((kalimat, harapan, tebakan, skor))
    return 100 * (len(data) - len(salah)) / len(data), salah


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tema", default="marshall")
    ap.add_argument("--ambang", type=float, default=DEFAULT_THRESHOLD)
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--salah", action="store_true", help="hanya tampilkan yang salah")
    args = ap.parse_args()

    themes = load_themes(BASE_DIR / "themes")
    if args.tema not in themes:
        sys.exit(f"Tema '{args.tema}' tidak ada. Pilihan: {', '.join(themes)}")
    data = baca_csv(BASE_DIR / "evaluasi" / f"{args.tema}.csv")

    if args.sweep:
        print(f"{'Ambang':<8}Akurasi")
        for a in SWEEP:
            akurasi, _ = nilai(ChatbotEngine(themes[args.tema], threshold=a), data)
            print(f"{a:<8.2f}{akurasi:5.1f}%")
        return

    engine = ChatbotEngine(themes[args.tema], threshold=args.ambang)
    akurasi, salah = nilai(engine, data)
    benar = len(data) - len(salah)
    print(f"Tema {args.tema}, ambang {args.ambang}: {benar} benar dari {len(data)} = {akurasi:.1f}%")
    if salah:
        print("\nKalimat yang salah (tambahkan polanya di themes/*.json):")
        for kalimat, harapan, tebakan, skor in salah:
            print(f"  \"{kalimat}\"\n     harapan: {harapan}, tebakan: {tebakan} (skor {skor:.2f})")
    elif not args.salah:
        print("Semua kalimat uji dikenali.")


if __name__ == "__main__":
    main()
