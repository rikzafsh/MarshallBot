"""
Evaluasi akurasi MarshallBot dengan data uji (kalimat yang TIDAK ada di file tema).

File data uji: evaluasi/<tema>.csv berkolom: kalimat,intent
Gunakan intent "fallback" untuk pertanyaan di luar tema (bot seharusnya menolak).

Contoh:
    python evaluate.py
    python evaluate.py --sweep      # coba banyak ambang batas
"""
import argparse
import csv
from collections import Counter
from pathlib import Path

from chatbot import ChatbotEngine, load_themes

BASE_DIR = Path(__file__).resolve().parent


def baca_data(tema):
    path = BASE_DIR / "evaluasi" / f"{tema}.csv"
    with open(path, encoding="utf-8") as f:
        return [(r["kalimat"], r["intent"]) for r in csv.DictReader(f)]


def evaluasi(theme, data, ambang):
    bot = ChatbotEngine(theme, ambang)      # klasifikasi saja, tanpa handler
    hasil = []
    for kalimat, harapan in data:
        tebakan, skor = bot.classify(kalimat)
        tebakan = tebakan or "fallback"
        hasil.append((kalimat, harapan, tebakan, skor))
    benar = sum(1 for _, h, t, _ in hasil if h == t)
    return benar / len(hasil), hasil


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tema", default="marshall")
    parser.add_argument("--ambang", type=float, default=0.45)
    parser.add_argument("--sweep", action="store_true", help="bandingkan beberapa ambang")
    args = parser.parse_args()

    theme = load_themes(BASE_DIR / "themes")[args.tema]
    data = baca_data(args.tema)

    if args.sweep:
        print(f"Tema {args.tema}: {len(data)} kalimat uji\n")
        print("ambang  akurasi")
        for a in [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.70]:
            akurasi, _ = evaluasi(theme, data, a)
            print(f" {a:.2f}   {akurasi:6.1%}  " + "#" * round(akurasi * 30))
        return

    akurasi, hasil = evaluasi(theme, data, args.ambang)
    print(f"Tema {args.tema} · ambang {args.ambang} · {len(data)} kalimat uji")
    print(f"Akurasi: {akurasi:.1%}\n")

    total = Counter(h for _, h, _, _ in hasil)
    benar = Counter(h for _, h, t, _ in hasil if h == t)
    print(f"{'intent':<28}{'benar':>6}{'total':>7}")
    for intent in sorted(total):
        print(f"{intent:<28}{benar[intent]:>6}{total[intent]:>7}")

    salah = [x for x in hasil if x[1] != x[2]]
    if salah:
        print("\nKalimat yang salah ditebak:")
        for kalimat, harapan, tebakan, skor in salah:
            print(f"- \"{kalimat}\" -> {tebakan} ({skor:.2f}), seharusnya {harapan}")


if __name__ == "__main__":
    main()
