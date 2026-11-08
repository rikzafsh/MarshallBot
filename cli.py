"""Chat di terminal, tanpa web. Contoh: python cli.py --debug"""
from __future__ import annotations

import argparse
import sys

from app import BASE_DIR, load_themes
from chatbot.engine import ChatbotEngine, DEFAULT_THRESHOLD
from chatbot.handlers import HANDLERS


def main() -> None:
    ap = argparse.ArgumentParser(description="Chat dengan bot di terminal")
    ap.add_argument("--tema", default="marshall", help="id tema (nama file di themes/)")
    ap.add_argument("--debug", action="store_true", help="tampilkan tiga kandidat teratas")
    ap.add_argument("--ambang", type=float, default=DEFAULT_THRESHOLD)
    args = ap.parse_args()

    themes = load_themes(BASE_DIR / "themes")
    if args.tema not in themes:
        sys.exit(f"Tema '{args.tema}' tidak ada. Pilihan: {', '.join(themes)}")
    bot = ChatbotEngine(themes[args.tema], threshold=args.ambang, handlers=HANDLERS)

    print(bot.isi(themes[args.tema]["greeting"]))
    print("(ketik 'keluar' untuk berhenti)\n")
    terakhir = None
    while True:
        try:
            pesan = input("Anda: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if pesan.lower() in {"keluar", "exit", "quit"}:
            break
        if not pesan:
            continue
        hasil = bot.reply(pesan, terakhir=terakhir)
        terakhir = hasil["reply"]
        print(f"Bot : {hasil['reply']}")
        if args.debug:
            label = hasil["intent"] or "tidak dikenali"
            print(f"      [intent: {label}, skor {hasil['score']:.2f}, status {hasil['status']}]")
            for c in bot.explain(pesan):
                print(f"      - {c['intent']:<26} {c['score']:.2f}  pola: \"{c['pattern']}\"")
        print()


if __name__ == "__main__":
    main()
