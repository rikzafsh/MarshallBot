"""
Chat dengan MarshallBot langsung di terminal, tanpa browser.

Contoh:
    python cli.py
    python cli.py --debug          # tampilkan 3 kandidat intent teratas
Ketik 'keluar' untuk berhenti.
"""
import argparse
from pathlib import Path

from chatbot import ChatbotEngine, load_themes
from chatbot.handlers import HANDLERS

BASE_DIR = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="MarshallBot di terminal")
    parser.add_argument("--tema", default="marshall", help="id tema (nama file JSON tanpa .json)")
    parser.add_argument("--ambang", type=float, default=0.45, help="ambang batas skor")
    parser.add_argument("--debug", action="store_true", help="tampilkan kandidat intent")
    args = parser.parse_args()

    themes = load_themes(BASE_DIR / "themes")
    if args.tema not in themes:
        print(f"Tema '{args.tema}' tidak ada. Pilihan: {', '.join(themes)}")
        return
    theme = themes[args.tema]
    bot = ChatbotEngine(theme, args.ambang, handlers=HANDLERS)

    print(f"{theme['avatar']} {theme['bot_name']}: {bot.isi(theme['greeting'])}")
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
        hasil = bot.reply(pesan, terakhir=terakhir)
        terakhir = hasil["reply"]
        print(f"{theme['bot_name']}: {hasil['reply']}")
        label = hasil["intent"] or "tidak dikenali"
        print(f"   [intent: {label} · skor {hasil['score']:.2f}]")
        if args.debug:
            for i, k in enumerate(bot.explain(pesan), 1):
                print(f"   {i}. {k['intent']:<24} {k['score']:.2f}  pola: \"{k['pattern']}\"")
        print()
    print("Sampai jumpa!")


if __name__ == "__main__":
    main()
