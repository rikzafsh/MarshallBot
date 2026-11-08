"""MarshallBot: chatbot tematik Kalender Jawa Mataraman (Sultanagungan).

Jalankan:   python app.py            (http://127.0.0.1:5000)
Produksi:   waitress-serve --port=8000 --call app:create_app
"""
from __future__ import annotations

import hmac
import json
import os
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, session

from chatbot.database import ChatHistory
from chatbot.engine import ChatbotEngine, DEFAULT_THRESHOLD, validate_theme
from chatbot.handlers import HANDLERS

BASE_DIR = Path(__file__).resolve().parent
MAKS_PESAN = 500


def load_themes(directory: str | os.PathLike) -> dict[str, dict]:
    """Muat semua themes/*.json; tema tidak valid menghentikan aplikasi."""
    themes: dict[str, dict] = {}
    for path in sorted(Path(directory).glob("*.json")):
        with open(path, encoding="utf-8") as f:
            theme = json.load(f)
        errors = validate_theme(theme)
        if errors:
            raise ValueError(f"{path.name} tidak valid: " + "; ".join(errors))
        themes[theme["id"]] = theme
    if not themes:
        raise ValueError(f"Tidak ada file tema di {directory}")
    return themes


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-ganti-di-produksi"),
        THRESHOLD=float(os.environ.get("THRESHOLD", DEFAULT_THRESHOLD)),
        DATABASE=os.environ.get("DATABASE", str(BASE_DIR / "chat_history.db")),
        ADMIN_KEY=os.environ.get("ADMIN_KEY", ""),
        THEMES_DIR=str(BASE_DIR / "themes"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 30,
        JSON_AS_ASCII=False,
    )
    if config:
        app.config.update(config)

    themes = load_themes(app.config["THEMES_DIR"])
    engines = {tid: ChatbotEngine(t, threshold=app.config["THRESHOLD"], handlers=HANDLERS)
               for tid, t in themes.items()}
    history = ChatHistory(app.config["DATABASE"])
    tema_utama = next(iter(themes))

    # --- pembantu ------------------------------------------------------------
    def get_session_id() -> str:
        if "sid" not in session:
            session["sid"] = uuid.uuid4().hex
            session.permanent = True
        return session["sid"]

    def tema_publik(tid: str) -> dict:
        t = themes[tid]
        return {"id": t["id"], "bot_name": t["bot_name"], "title": t["title"],
                "subtitle": t.get("subtitle", ""), "description": t.get("description", ""),
                "avatar": t.get("avatar", "?"), "color": t.get("color", "#D2562D"),
                "suggestions": t.get("suggestions", []),
                "greeting": engines[tid].isi(t.get("greeting", "")),
                "intents": len(t["intents"])}

    def galat(pesan: str, kode: int = 400):
        return jsonify({"error": pesan}), kode

    def periksa_kunci_admin() -> bool:
        kunci = app.config["ADMIN_KEY"]
        if not kunci:
            return True
        return hmac.compare_digest(request.args.get("key", ""), kunci)

    def baca_permintaan():
        """Validasi body JSON: kembalikan (theme_id, message, None) atau (.., .., galat)."""
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return None, None, galat("Body harus berformat JSON")
        tid = data.get("theme") or (tema_utama if len(themes) == 1 else None)
        if tid not in engines:
            return None, None, galat("Tema tidak dikenal")
        pesan = data.get("message", "")
        if not isinstance(pesan, str):
            return None, None, galat("Pesan harus berupa teks")
        pesan = pesan.strip()
        if not pesan:
            return None, None, galat("Pesan tidak boleh kosong")
        if len(pesan) > MAKS_PESAN:
            return None, None, galat(f"Pesan maksimal {MAKS_PESAN} karakter")
        return tid, pesan, None

    # --- halaman -------------------------------------------------------------
    @app.get("/")
    def index():
        return render_template("index.html", themes=[tema_publik(t) for t in themes],
                               contoh=themes[tema_utama].get("suggestions", []))

    @app.get("/chat/<theme_id>")
    def chat_page(theme_id):
        if theme_id not in themes:
            return render_template("404.html"), 404
        return render_template("chat.html", tema=tema_publik(theme_id))

    @app.get("/admin/<theme_id>")
    def admin_page(theme_id):
        if theme_id not in themes:
            return render_template("404.html"), 404
        if not periksa_kunci_admin():
            return galat("Kunci admin salah", 403)
        return render_template("admin.html", tema=tema_publik(theme_id),
                               stats=history.stats(theme_id),
                               threshold=app.config["THRESHOLD"])

    @app.errorhandler(404)
    def tidak_ada(_):
        if request.path.startswith("/api/"):
            return galat("Alamat tidak ditemukan", 404)
        return render_template("404.html"), 404

    # --- REST API ------------------------------------------------------------
    @app.get("/api/themes")
    def api_themes():
        return jsonify([tema_publik(t) for t in themes])

    @app.post("/api/chat")
    def api_chat():
        tid, pesan, err = baca_permintaan()
        if err:
            return err
        sid = get_session_id()
        terakhir = history.last_bot_reply(sid, tid)
        hasil = engines[tid].reply(pesan, terakhir=terakhir)
        history.add(sid, tid, "user", pesan, hasil["intent"], hasil["score"])
        history.add(sid, tid, "bot", hasil["reply"], hasil["intent"], hasil["score"])
        return jsonify(hasil)

    @app.post("/api/explain")
    def api_explain():
        tid, pesan, err = baca_permintaan()
        if err:
            return err
        return jsonify({"threshold": app.config["THRESHOLD"],
                        "candidates": engines[tid].explain(pesan)})

    @app.get("/api/history/<theme_id>")
    def api_history(theme_id):
        if theme_id not in themes:
            return galat("Tema tidak ditemukan", 404)
        return jsonify(history.get(get_session_id(), theme_id))

    @app.delete("/api/history/<theme_id>")
    def api_history_hapus(theme_id):
        if theme_id not in themes:
            return galat("Tema tidak ditemukan", 404)
        return jsonify({"deleted": history.clear(get_session_id(), theme_id)})

    @app.get("/api/stats/<theme_id>")
    def api_stats(theme_id):
        if theme_id not in themes:
            return galat("Tema tidak ditemukan", 404)
        if not periksa_kunci_admin():
            return galat("Kunci admin salah", 403)
        return jsonify(history.stats(theme_id))

    return app


if __name__ == "__main__":
    # debug=True hanya untuk komputer sendiri: FLASK_DEBUG=1 python app.py
    create_app().run(debug=os.environ.get("FLASK_DEBUG") == "1")
