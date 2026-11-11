"""Uji integrasi route Flask menggunakan test client (database sementara)."""
from app import create_app


def buat(tmp_path, **ekstra):
    config = {"TESTING": True, "DATABASE": str(tmp_path / "test.db"), "ADMIN_KEY": ""}
    config.update(ekstra)
    return create_app(config)


def kirim(client, pesan, tema="marshall"):
    return client.post("/api/chat", json={"message": pesan, "theme": tema})


def test_halaman_utama_menampilkan_tema(tmp_path):
    res = buat(tmp_path).test_client().get("/")
    assert res.status_code == 200
    assert "Konversi Kalender Jawa Mataraman" in res.get_data(as_text=True) or "MarshallBot" in res.get_data(as_text=True)


def test_halaman_chat_tidak_membocorkan_daftar_intent(tmp_path):
    html = buat(tmp_path).test_client().get("/chat/marshall").get_data(as_text=True)
    assert "MarshallBot" in html and "gregorian_to_weton" not in html


def test_tema_tidak_ada_404(tmp_path):
    c = buat(tmp_path).test_client()
    assert c.get("/chat/tidak-ada").status_code == 404
    assert c.get("/api/history/tidak-ada").status_code == 404
    assert c.get("/rute-ngawur").status_code == 404


def test_api_themes(tmp_path):
    data = buat(tmp_path).test_client().get("/api/themes").get_json()
    assert [t["id"] for t in data] == ["marshall"]


def test_api_chat_berhasil(tmp_path):
    res = kirim(buat(tmp_path).test_client(), "Apa itu windu?")
    d = res.get_json()
    assert res.status_code == 200 and d["intent"] == "year_cycle" and d["reply"]


def test_api_chat_konversi_dari_kode_acuan(tmp_path):
    d = kirim(buat(tmp_path).test_client(), "Weton tanggal 17 Agustus 1945 apa?").get_json()
    assert d["intent"] == "gregorian_to_weton" and "Jumat Legi" in d["reply"]


def test_api_chat_input_tidak_valid(tmp_path):
    c = buat(tmp_path).test_client()
    for payload in ({"message": "", "theme": "marshall"}, {"message": "   ", "theme": "marshall"},
                    {"message": "halo", "theme": "salah"}, {"message": "a" * 501, "theme": "marshall"},
                    {"message": 123, "theme": "marshall"}, {}):
        assert c.post("/api/chat", json=payload).status_code == 400, payload
    assert c.post("/api/chat", data="bukan json", content_type="text/plain").status_code == 400


def test_riwayat_tersimpan_per_sesi_dan_bisa_dihapus(tmp_path):
    app = buat(tmp_path)
    a, b = app.test_client(), app.test_client()
    kirim(a, "halo")
    assert [r["sender"] for r in a.get("/api/history/marshall").get_json()] == ["user", "bot"]
    assert b.get("/api/history/marshall").get_json() == []          # sesi lain terpisah
    a.delete("/api/history/marshall")
    assert a.get("/api/history/marshall").get_json() == []


def test_ulangi_jawaban_memakai_riwayat_sesi(tmp_path):
    c = buat(tmp_path).test_client()
    kirim(c, "Apa itu selapanan?")
    d = kirim(c, "Bisa ulangi jawaban tadi?").get_json()
    assert d["intent"] == "repeat_response" and "35 hari" in d["reply"]


def test_html_dan_sql_disimpan_apa_adanya(tmp_path):
    c = buat(tmp_path).test_client()
    kirim(c, "<script>alert(1)</script>")
    kirim(c, "'); DROP TABLE messages; --")
    h = c.get("/api/history/marshall").get_json()
    assert len(h) == 4 and h[0]["text"] == "<script>alert(1)</script>"


def test_statistik_intent(tmp_path):
    c = buat(tmp_path).test_client()
    kirim(c, "halo")
    assert c.get("/api/stats/marshall").get_json()[0]["intent"] == "greeting"


def test_api_explain(tmp_path):
    d = buat(tmp_path).test_client().post(
        "/api/explain", json={"message": "weton 17 Agustus 1945", "theme": "marshall"}).get_json()
    assert d["threshold"] == 0.45 and d["candidates"][0]["intent"] == "gregorian_to_weton"


def test_halaman_admin_menampilkan_pertanyaan_tak_dikenali(tmp_path):
    c = buat(tmp_path).test_client()
    kirim(c, "harga bensin berapa")
    html = c.get("/admin/marshall").get_data(as_text=True)
    assert "harga bensin berapa" in html and "tidak dikenali" in html


def test_admin_key_melindungi_halaman_admin(tmp_path):
    c = buat(tmp_path, ADMIN_KEY="rahasia").test_client()
    assert c.get("/admin/marshall").status_code == 403
    assert c.get("/admin/marshall?key=salah").status_code == 403
    assert c.get("/api/stats/marshall").status_code == 403
    assert c.get("/admin/marshall?key=rahasia").status_code == 200
