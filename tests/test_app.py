"""Uji integrasi: route dipanggil lewat Flask test client dengan database sementara."""
from app import create_app


def buat(tmp_path, **ekstra):
    config = {"TESTING": True, "DATABASE": str(tmp_path / "t.db"), "ADMIN_KEY": ""}
    config.update(ekstra)
    return create_app(config)


def test_halaman_utama_dan_chat(tmp_path):
    c = buat(tmp_path).test_client()
    assert "MarshallBot" in c.get("/").get_data(as_text=True)
    assert c.get("/chat/marshall").status_code == 200


def test_tema_tidak_ada_404(tmp_path):
    c = buat(tmp_path).test_client()
    assert c.get("/chat/tidakada").status_code == 404
    assert c.get("/api/history/tidakada").status_code == 404
    assert c.get("/rute-ngawur").status_code == 404


def test_api_themes(tmp_path):
    data = buat(tmp_path).test_client().get("/api/themes").get_json()
    assert data[0]["id"] == "marshall" and data[0]["intents"] == 46


def test_api_chat_berhasil(tmp_path):
    r = buat(tmp_path).test_client().post("/api/chat", json={"message": "Apa itu windu?", "theme": "marshall"})
    d = r.get_json()
    assert r.status_code == 200 and d["intent"] == "year_cycle" and d["status"] == "ok"


def test_api_chat_tema_bawaan_bila_satu_tema(tmp_path):
    r = buat(tmp_path).test_client().post("/api/chat", json={"message": "halo"})
    assert r.status_code == 200


def test_api_chat_input_tidak_valid(tmp_path):
    c = buat(tmp_path).test_client()
    for payload in ({"message": "", "theme": "marshall"}, {"message": "   ", "theme": "marshall"},
                    {"message": "x" * 501, "theme": "marshall"}, {"message": "halo", "theme": "salah"},
                    {"message": 123, "theme": "marshall"}):
        r = c.post("/api/chat", json=payload)
        assert r.status_code == 400 and "error" in r.get_json(), payload
    assert c.post("/api/chat", data="bukan json", content_type="text/plain").status_code == 400


def test_riwayat_tersimpan_per_sesi_dan_bisa_dihapus(tmp_path):
    app = buat(tmp_path)
    a, b = app.test_client(), app.test_client()
    a.post("/api/chat", json={"message": "halo"})
    h = a.get("/api/history/marshall").get_json()
    assert [m["sender"] for m in h] == ["user", "bot"]
    assert b.get("/api/history/marshall").get_json() == []          # sesi lain terpisah
    assert a.delete("/api/history/marshall").get_json()["deleted"] == 2
    assert a.get("/api/history/marshall").get_json() == []


def test_ulangi_jawaban_memakai_riwayat_sesi(tmp_path):
    c = buat(tmp_path).test_client()
    c.post("/api/chat", json={"message": "Apa itu selapanan?"})
    r = c.post("/api/chat", json={"message": "Bisa ulangi jawaban tadi?"}).get_json()
    assert r["intent"] == "repeat_response" and "35 hari" in r["reply"]


def test_pesan_berisi_html_disimpan_apa_adanya(tmp_path):
    c = buat(tmp_path).test_client()
    c.post("/api/chat", json={"message": "<script>alert(1)</script>"})
    h = c.get("/api/history/marshall").get_json()
    assert h[0]["text"] == "<script>alert(1)</script>"   # escape dilakukan di browser (textContent)


def test_sql_injection_tidak_merusak(tmp_path):
    c = buat(tmp_path).test_client()
    c.post("/api/chat", json={"message": "'); DROP TABLE messages; --"})
    assert len(c.get("/api/history/marshall").get_json()) == 2


def test_api_explain(tmp_path):
    d = buat(tmp_path).test_client().post(
        "/api/explain", json={"message": "weton 17 Agustus 1945", "theme": "marshall"}).get_json()
    assert len(d["candidates"]) == 3 and d["candidates"][0]["intent"] == "gregorian_to_weton"


def test_statistik_dan_halaman_admin(tmp_path):
    c = buat(tmp_path).test_client()
    c.post("/api/chat", json={"message": "halo"})
    c.post("/api/chat", json={"message": "harga bensin berapa"})
    s = c.get("/api/stats/marshall").get_json()
    assert s["total"] == 2 and s["tidak_dikenali"] == 1 and s["persen_dikenali"] == 50.0
    html = c.get("/admin/marshall").get_data(as_text=True)
    assert "harga bensin berapa" in html


def test_admin_key_melindungi_halaman_admin(tmp_path):
    c = buat(tmp_path, ADMIN_KEY="rahasia").test_client()
    assert c.get("/admin/marshall").status_code == 403
    assert c.get("/admin/marshall?key=salah").status_code == 403
    assert c.get("/api/stats/marshall").status_code == 403
    assert c.get("/admin/marshall?key=rahasia").status_code == 200
