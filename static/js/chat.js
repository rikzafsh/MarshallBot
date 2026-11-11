/* Antarmuka chat: mengirim pesan dengan fetch() tanpa memuat ulang halaman.
 * Semua teks ditampilkan lewat textContent (aman dari XSS), tidak pernah innerHTML. */
(() => {
  const tema = JSON.parse(document.getElementById("boot").textContent);
  const el = {
    list: document.getElementById("messages"),
    form: document.getElementById("chat-form"),
    input: document.getElementById("chat-input"),
    chips: document.getElementById("suggestions"),
    clear: document.getElementById("btn-clear"),
    belajar: document.getElementById("mode-belajar"),
    admin: document.getElementById("link-admin"),
  };
  let sibuk = false;

  const skor = (n) => Number(n).toFixed(2).replace(".", ",");

  function gulirKeBawah() {
    el.list.scrollTop = el.list.scrollHeight;
  }

  function metaTeks(intent, score) {
    if (score === null || score === undefined) return "";
    return intent ? `intent ${intent}, skor ${skor(score)}` : `tidak dikenali, skor ${skor(score)}`;
  }

  /** Tambah satu gelembung. kelas: "user" | "bot". Mengembalikan elemen pembungkus. */
  function tambahPesan(kelas, teks, { meta = "", status = "ok" } = {}) {
    const wrap = document.createElement("div");
    wrap.className = `msg msg-${kelas}`;
    if (status === "perlu_info" || status === "perhitungan_belum_aktif") wrap.classList.add("is-note");
    if (status === "galat") wrap.classList.add("is-error");

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = teks;
    wrap.appendChild(bubble);

    if (meta) {
      const m = document.createElement("div");
      m.className = "meta";
      m.textContent = meta;
      wrap.appendChild(m);
    }
    el.list.appendChild(wrap);
    gulirKeBawah();
    return wrap;
  }

  function tambahPenjelasan(wrap, data) {
    const ul = document.createElement("ul");
    ul.className = "explain";
    data.candidates.forEach((c, i) => {
      const lolos = c.score >= data.threshold;
      const li = document.createElement("li");
      li.className = lolos ? "pass" : "";
      li.textContent = `${i + 1}. ${c.intent} ${skor(c.score)} ` +
        `(${lolos ? "lolos ambang" : "di bawah ambang"}), pola "${c.pattern}"`;
      ul.appendChild(li);
    });
    wrap.appendChild(ul);
    gulirKeBawah();
  }

  function tambahKetik() {
    const wrap = document.createElement("div");
    wrap.className = "msg msg-bot";
    const b = document.createElement("div");
    b.className = "bubble typing";
    b.setAttribute("aria-label", `${tema.bot_name} sedang mengetik`);
    b.innerHTML = "<i></i><i></i><i></i>"; // konstanta, tanpa data pengguna
    wrap.appendChild(b);
    el.list.appendChild(wrap);
    gulirKeBawah();
    return wrap;
  }

  async function panggil(url, opsi) {
    const res = await fetch(url, opsi);
    let data = null;
    try { data = await res.json(); } catch (_) { /* body bukan JSON */ }
    return { res, data };
  }

  const kirimJson = (url, badan) => panggil(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(badan),
  });

  async function kirimPesan(teks) {
    teks = teks.trim();
    if (!teks || sibuk) return;          // pesan kosong tidak dikirim ke server
    sibuk = true;
    tambahPesan("user", teks);
    el.input.value = "";
    const ketik = tambahKetik();
    try {
      const { res, data } = await kirimJson("/api/chat", { message: teks, theme: tema.id });
      ketik.remove();
      if (!res.ok) {
        tambahPesan("bot", (data && data.error) || "Terjadi kesalahan pada server.", { status: "galat" });
        return;
      }
      const wrap = tambahPesan("bot", data.reply, {
        meta: metaTeks(data.intent, data.score), status: data.status,
      });
      if (el.belajar.checked) {
        const ex = await kirimJson("/api/explain", { message: teks, theme: tema.id });
        if (ex.res.ok) tambahPenjelasan(wrap, ex.data);
      }
    } catch (err) {
      ketik.remove();
      tambahPesan("bot", "Gagal terhubung ke server. Periksa koneksi lalu coba lagi.", { status: "galat" });
    } finally {
      sibuk = false;
      el.input.focus();
    }
  }

  function tampilkanSapaan() {
    tambahPesan("bot", tema.greeting);
  }

  async function muatRiwayat() {
    try {
      const { res, data } = await panggil(`/api/history/${encodeURIComponent(tema.id)}`);
      if (res.ok && Array.isArray(data) && data.length) {
        data.forEach((m) => tambahPesan(
          m.sender === "user" ? "user" : "bot", m.text,
          m.sender === "bot" ? { meta: metaTeks(m.intent, m.score) } : {}));
        return;
      }
    } catch (_) { /* tampilkan sapaan saja */ }
    tampilkanSapaan();
  }

  function isiSaran() {
    tema.suggestions.forEach((s) => {
      const li = document.createElement("li");
      const b = document.createElement("button");
      b.type = "button";
      b.className = "chip";
      b.textContent = s;
      b.addEventListener("click", () => kirimPesan(s));
      li.appendChild(b);
      el.chips.appendChild(li);
    });
  }

  el.form.addEventListener("submit", (e) => {
    e.preventDefault();                  // jangan muat ulang halaman
    kirimPesan(el.input.value);
  });

  el.clear.addEventListener("click", async () => {
    if (!window.confirm("Hapus seluruh riwayat percakapan ini?")) return;
    try {
      await panggil(`/api/history/${encodeURIComponent(tema.id)}`, { method: "DELETE" });
    } catch (_) { /* abaikan; tampilan tetap dibersihkan */ }
    el.list.replaceChildren();
    tampilkanSapaan();
  });

  // Teruskan ?key= ke tautan statistik bila halaman dibuka dengan kunci admin.
  const kunci = new URLSearchParams(location.search).get("key");
  if (kunci && el.admin) el.admin.href += `?key=${encodeURIComponent(kunci)}`;

  // ?q=... dari beranda: isi kotak input, pengguna tinggal menekan Kirim.
  const q = new URLSearchParams(location.search).get("q");
  if (q) el.input.value = q.slice(0, 500);

  isiSaran();
  muatRiwayat();
})();
