"""Streamlit UI for Method 2 (2DLMUTF + RSA/ECC) research adaptation.

All user-uploaded data is processed in RAM. No uploaded keys/images are
intentionally persisted on disk. Keep the VPS private and enable HTTPS.
"""
from __future__ import annotations

import hmac
import json
import os
import time
from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

from web_adapter import (
    encrypt_image, decrypt_image, encryption_archive, extract_encrypted_archive,
    extra_experiments, generate_keypair, get_backend, image_from_bytes,
    make_archive, metadata_bytes, metrics_csv, png_bytes, safe_metrics,
)
from chaos_image_encryption.comparison import compare_methods

st.set_page_config(page_title="Metode 2 | Enkripsi Citra Chaos", page_icon="🔐", layout="wide")


def format_float(v, decimals=4):
    if v == "inf":
        return "∞"
    return f"{float(v):.{decimals}f}"


def download_button(label, content: bytes, name: str, mime: str = "application/octet-stream", key=None):
    st.download_button(label, data=content, file_name=name, mime=mime, key=key)


def graph_histograms(images: dict[str, np.ndarray]) -> None:
    fig, axes = plt.subplots(1, len(images), figsize=(12, 3.2))
    if not isinstance(axes, np.ndarray):
        axes = [axes]
    for ax, (label, arr) in zip(axes, images.items()):
        counts = np.bincount(arr.reshape(-1), minlength=256)
        ax.plot(range(256), counts, linewidth=1)
        ax.set_title(label)
        ax.set_xlabel("Intensitas pixel")
        ax.set_ylabel("Frekuensi")
        ax.grid(alpha=0.2)
    fig.tight_layout()
    st.pyplot(fig, clear_figure=True)
    plt.close(fig)


def enforce_login() -> None:
    app_password = os.getenv("APP_PASSWORD", "")
    if not app_password or app_password == "CHANGE_THIS_TO_A_LONG_UNIQUE_PASSWORD":
        st.error("APP_PASSWORD belum dikonfigurasi. Atur dulu password aplikasi pada VPS (lihat README).")
        st.stop()
    if not st.session_state.get("authenticated", False):
        st.title("🔐 Akses Program Penelitian")
        st.write("Masukkan password aplikasi untuk membuka halaman enkripsi.")
        with st.form("login"):
            pwd = st.text_input("Password aplikasi", type="password")
            submitted = st.form_submit_button("Masuk", type="primary")
        if submitted:
            if hmac.compare_digest(pwd.encode("utf-8"), app_password.encode("utf-8")):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Password tidak sesuai.")
        st.stop()


enforce_login()

with st.sidebar:
    st.title("🔐 Metode 2")
    st.caption("2DLMUTF · RSA / X25519 · Diffusion v3")
    st.write("Untuk percobaan enkripsi citra dan pengujian metode.")
    st.caption("Created by Mohamad Idris, S.Si., M.Sc.")
    st.divider()
    page = st.radio("Navigasi", ["🖼️ Aplikasi", "📖 Alur Program", "📊 Bandingkan Metode"], index=0)
    if st.button("Hapus data sesi & keluar", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    st.divider()
    st.info("Batas gambar: 2 juta pixel. Foto resolusi tinggi sebaiknya diperkecil dahulu.")
    st.warning("Demo penelitian, belum melalui audit keamanan kriptografi. Jangan pakai untuk dokumen sensitif.")



def show_process_page() -> None:
    st.title("📖 Alur Program — Metode 2")
    st.caption("Gambaran sederhana proses enkripsi dan dekripsi citra menggunakan RSA/ECC + 2DLMUTF")
    st.write("Halaman ini menjelaskan cara kerja program secara garis besar, bukan panduan teknis yang rumit.")
    st.info("Adaptasi penelitian: persamaan 2DLMUTF mengikuti Ahmad dkk. (2025), sedangkan permutation, diffusion v3, dan RSA/ECC dipertahankan dari Metode 1. Artikel asli memakai deret 2DLMUTF untuk membentuk S-box. DOI: 10.1038/s41598-025-04702-0")

    flow_enc, flow_dec = st.tabs(["🔒 Alur Enkripsi", "🔓 Alur Dekripsi"])
    with flow_enc:
        st.image("assets/alur_enkripsi.png", use_container_width=True)
        st.markdown("""
        **Intinya:** gambar asli diacak posisi pixel-nya (*permutation*), lalu nilai pixel diubah (*diffusion*) menggunakan deret bilangan dari 2DLMUTF. RSA atau ECC dipakai untuk mengamankan/membentuk *session key*, bukan mengenkripsi pixel satu per satu.

        **File keluaran:** `cipher.png` (gambar terenkripsi) dan `metadata.json` (informasi untuk mengulang proses saat dekripsi). Private key **tidak** dimasukkan ke metadata.
        """)
    with flow_dec:
        st.image("assets/alur_dekripsi.png", use_container_width=True)
        st.markdown("""
        **Intinya:** dengan private key yang sesuai dan metadata, program menghasilkan ulang deret chaos yang sama. Proses diffusion dan permutation dibalik sehingga gambar kembali seperti semula.

        Pada gambar tanpa gangguan, **exact match = True**, **MSE = 0**, **PSNR = ∞**, dan **SSIM = 1**.
        """)

    st.divider()
    st.subheader("Rumus yang digunakan (ringkas)")
    st.write("**1. Pembangkit chaos — 2DLMUTF (Ahmad et al., 2025)**")
    st.latex(r"x_{n+1}=\operatorname{mod}\left(\frac{r_1+x_n(1-x_n)}{y_n(1-y_n)},1\right)")
    st.latex(r"y_{n+1}=\operatorname{mod}\left(\frac{r_2+y_n(1-y_n)}{x_n(1-x_{n+1})},1\right)")
    st.caption("Implementasi: r₁ = 4,0 dan r₂ = 3,8; burn-in = 1.000. x₀ dan y₀ diturunkan dari session key melalui HKDF-SHA256. Nilai mendekati singularitas diberi pelindung numerik 10⁻¹² untuk stabilitas float64.")

    st.write("**2. Permutation (mengacak posisi pixel)**")
    st.latex(r"\pi=\operatorname{argsort}(X),\qquad P'=P[\pi]")
    st.caption("X adalah deret 2DLMUTF yang dipakai untuk menentukan urutan baru posisi pixel. Pada dekripsi digunakan inverse permutation.")

    st.write("**3. Diffusion v3 (mengubah nilai pixel)**")
    st.latex(r"q_i=S(P'_i\oplus k_{1,i})")
    st.latex(r"F_i=(a_iF_{i-1}+q_i+k_{2,i})\bmod 256")
    st.caption("S adalah substitusi byte yang dapat dibalik (S-box). aᵢ merupakan bilangan ganjil agar operasi feedback dapat dibalik modulo 256. Dalam kode, proses nonlinear ini dilanjutkan dengan jalur balik arah dan dua round; rumus di atas hanya potongan utama agar mudah dibaca.")

    st.divider()
    st.subheader("Pengujian yang ada di program")
    st.markdown("""
    - **PSNR dan SSIM:** membandingkan gambar asli dan hasil dekripsi.
    - **Histogram, entropy, correlation:** melihat perubahan statistik setelah enkripsi.
    - **NPCR dan UACI:** melihat efek perubahan kecil pada citra asli terhadap ciphertext.
    - **Key sensitivity:** melihat hasil jika session key diubah satu bit.
    - **Robustness:** mencoba noise, kehilangan sebagian area ciphertext, dan kompresi JPEG.

    Nilai statistik yang baik tidak otomatis membuktikan keamanan kriptografi. Program ini adalah **prototipe penelitian**.
    """)
    st.info("Ingin langsung mencoba? Pilih **🖼️ Aplikasi** di menu sebelah kiri, lalu buka tab **Demo satu klik**.")


def show_app_page() -> None:
    st.title("Enkripsi Citra Berbasis Chaos — Metode 2")
    st.caption("RSA / ECC + 2DLMUTF + Permutation + Nonlinear Diffusion v3")
    st.write("Pilih **Demo satu klik** jika hanya ingin mencoba alur lengkap. Untuk mengirim file enkripsi ke orang lain, gunakan tab **Enkripsi file** dan **Dekripsi file**.")

    tab_demo, tab_encrypt, tab_decrypt, tab_keys = st.tabs([
        "🖼️ Demo satu klik", "🔒 Enkripsi file", "🔓 Dekripsi file", "🗝️ Buat kunci"
    ])

    with tab_demo:
        st.subheader("1. Upload gambar dan jalankan")
        st.write("Program akan membuat key demo, mengenkripsi gambar, mendekripsi, lalu menghitung hasil evaluasi.")
        demo_file = st.file_uploader("Gambar asli", type=["png", "jpg", "jpeg", "avif", "webp", "bmp", "tif", "tiff"], key="demo_file")
        demo_crypto = st.radio("Pilih enkripsi asimetris", ["RSA", "ECC"], horizontal=True, key="demo_crypto")
        if st.button("Jalankan demo enkripsi + dekripsi", type="primary", disabled=demo_file is None):
            try:
                with st.spinner("Menghitung enkripsi dan dekripsi..."):
                    original, mode = image_from_bytes(demo_file.getvalue())
                    t0 = time.perf_counter()
                    private_pem, public_pem = generate_keypair(demo_crypto)
                    keygen_ms = 1000*(time.perf_counter()-t0)
                    t1 = time.perf_counter()
                    cipher, meta = encrypt_image(original, mode, public_pem)
                    enc_ms = 1000*(time.perf_counter()-t1)
                    t2 = time.perf_counter()
                    restored = decrypt_image(cipher, mode, meta, private_pem)
                    dec_ms = 1000*(time.perf_counter()-t2)
                    metrics = safe_metrics(original, cipher, restored)
                    st.session_state["demo_result"] = {
                        "original":original, "cipher":cipher, "restored":restored,
                        "mode":mode, "meta":meta, "private":private_pem, "public":public_pem,
                        "metrics":metrics, "backend":demo_crypto,
                        "keygen_ms":keygen_ms, "enc_ms":enc_ms, "dec_ms":dec_ms,
                        "source_name":demo_file.name,
                    }
                    st.session_state.pop("extra_results", None)
            except Exception as e:
                st.error(f"Gagal memproses gambar: {e}")

        result = st.session_state.get("demo_result")
        if result:
            st.success(f"Demo selesai: {result['source_name']} ({result['backend']})")
            original, cipher, restored = result["original"], result["cipher"], result["restored"]
            a, b, d = st.columns(3)
            with a:
                st.image(original, caption="Citra asli", use_container_width=True)
            with b:
                st.image(cipher, caption="Citra terenkripsi", use_container_width=True)
            with d:
                st.image(restored, caption="Citra hasil dekripsi", use_container_width=True)

            m = result["metrics"]
            correct = m["correctness"]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Exact recovery", "Ya" if correct["exact_match"] else "Tidak")
            c2.metric("PSNR dekripsi", format_float(correct["psnr_original_decrypted_db"], 2))
            c3.metric("SSIM dekripsi", format_float(correct["ssim_original_decrypted"], 4))
            c4.metric("Entropy cipher", format_float(m["entropy"]["encrypted"]["overall"], 5))
            st.caption(f"Durasi key generation {result['keygen_ms']:.1f} ms · encrypt {result['enc_ms']:.1f} ms · decrypt {result['dec_ms']:.1f} ms")
            with st.expander("Korelasi pixel dan histogram"):
                cor = m["correlation"]["encrypted"]
                st.write(f"Cipher correlation — horizontal: {cor['horizontal']:.6f}; vertikal: {cor['vertical']:.6f}; diagonal: {cor['diagonal']:.6f}")
                graph_histograms({"Asli":original, "Enkripsi":cipher, "Dekripsi":restored})

            st.markdown("#### Unduh hasil")
            mode = result["mode"]
            files = {
                "original.png":png_bytes(original, mode),
                "cipher.png":png_bytes(cipher, mode),
                "metadata.json":metadata_bytes(result["meta"]),
                "decrypted.png":png_bytes(restored, mode),
                "metrics.json":json.dumps(m, ensure_ascii=False, indent=2).encode("utf-8"),
                "metrics.csv":metrics_csv(m),
                "public.pem":result["public"],
                "README.txt":("Contoh Metode 2. Untuk decrypt manual, simpan private.pem secara TERPISAH. "
                               "Jangan upload private.pem ke GitHub atau bagikan sembarangan.\n").encode("utf-8"),
            }
            download_button("Download hasil demo (ZIP)", make_archive(files), "hasil_demo_metode2.zip", "application/zip", "demo_zip")
            download_button("Download private key DEMO (penting untuk decrypt)", result["private"], "private_demo.pem", "application/x-pem-file", "demo_priv")
            st.caption("Private key **tidak** disertakan di ZIP hasil. Simpan terpisah; jika hilang, ciphertext tersebut tidak dapat didekripsi kembali.")

            st.markdown("#### Pengujian tambahan (opsional)")
            st.write("Uji sederhana untuk gambaran NPCR/UACI, key sensitivity, serta noise, cropping-like, dan JPEG. Bukan pengujian statistik skala dataset.")
            if st.button("Jalankan pengujian tambahan", key="extra_btn"):
                try:
                    with st.spinner("Menghitung pengujian tambahan..."):
                        st.session_state["extra_results"] = extra_experiments(original, cipher, result["meta"], result["private"])
                except Exception as e:
                    st.error(f"Pengujian gagal: {e}")
            extra = st.session_state.get("extra_results")
            if extra:
                st.caption("**Differential:** satu bit gambar asli diubah, key dan nonce tetap sama. NPCR/UACI membandingkan dua ciphertext.")
                st.write("**Differential test (plaintext beda 1 bit):**", {k:round(v, 4) for k, v in extra["differential"].items()})
                st.caption("**Key sensitivity:** gambar dan nonce tetap sama, satu bit session key diubah. NPCR/UACI membandingkan dua ciphertext.")
                st.write("**Key sensitivity (session key beda 1 bit):**", {k:(round(v, 4) if isinstance(v, float) else v) for k,v in extra["key_sensitivity"].items()})
                st.dataframe(extra["attacks"], use_container_width=True, hide_index=True)
                download_button("Download pengujian tambahan JSON", json.dumps(extra, indent=2).encode("utf-8"), "pengujian_tambahan.json", "application/json", "extra_json")

    with tab_encrypt:
        st.subheader("Enkripsi gambar menggunakan public key")
        st.write("Upload gambar dan **public.pem** milik penerima. Download hasil sebagai ZIP yang berisi cipher.png + metadata.json.")
        enc_image = st.file_uploader("Gambar yang mau dienkripsi", type=["png","jpg","jpeg","avif","webp","bmp","tif","tiff"], key="enc_image")
        enc_public = st.file_uploader("Public key (PEM)", type=["pem"], key="enc_pub")
        if st.button("Encrypt", type="primary", disabled=not(enc_image and enc_public), key="encrypt_button"):
            try:
                with st.spinner("Mengenkripsi..."):
                    image, mode = image_from_bytes(enc_image.getvalue())
                    backend = get_backend(enc_public.getvalue())
                    cipher, meta = encrypt_image(image, mode, enc_public.getvalue())
                    st.session_state["manual_encrypt"] = {
                        "cipher":cipher, "mode":mode,
                        "zip":encryption_archive(cipher, mode, meta), "backend":backend,
                    }
            except Exception as e:
                st.error(f"Enkripsi gagal: {e}")
        enc = st.session_state.get("manual_encrypt")
        if enc:
            st.success(f"Enkripsi berhasil ({enc['backend']}).")
            st.image(enc["cipher"], caption="Citra terenkripsi", width=380)
            download_button("Download paket enkripsi ZIP", enc["zip"], "paket_enkripsi.zip", "application/zip", "enc_download")

    with tab_decrypt:
        st.subheader("Dekripsi gambar")
        st.write("Upload paket ZIP dari tab Enkripsi (atau ZIP hasil demo), lalu upload **private.pem** dari pasangan kunci yang sama.")
        dec_zip = st.file_uploader("Paket enkripsi ZIP", type=["zip"], key="dec_zip")
        dec_private = st.file_uploader("Private key (PEM)", type=["pem"], key="dec_priv")
        if st.button("Decrypt", type="primary", disabled=not(dec_zip and dec_private), key="dec_btn"):
            try:
                with st.spinner("Mendekripsi..."):
                    cipher, mode, meta = extract_encrypted_archive(dec_zip.getvalue())
                    decrypted = decrypt_image(cipher, mode, meta, dec_private.getvalue())
                    st.session_state["manual_decrypt"] = {"decrypted":decrypted, "mode":mode}
            except Exception as e:
                st.error(f"Dekripsi gagal. Periksa pasangan kunci dan metadata: {e}")
        dec = st.session_state.get("manual_decrypt")
        if dec:
            st.success("Dekripsi selesai.")
            st.image(dec["decrypted"], caption="Citra hasil dekripsi", width=380)
            download_button("Download gambar dekripsi PNG", png_bytes(dec["decrypted"], dec["mode"]), "decrypted.png", "image/png", "dec_download")

    with tab_keys:
        st.subheader("Buat pasangan kunci baru")
        st.write("Diperuntukkan untuk pengujian. Public key boleh dibagikan; private key harus disimpan sendiri.")
        backend = st.radio("Jenis key", ["RSA", "ECC"], horizontal=True, key="gen_backend")
        if st.button("Generate Key Pair", type="primary", key="makekeys"):
            try:
                private_pem, public_pem = generate_keypair(backend)
                st.session_state["generated_keys"] = (backend, private_pem, public_pem)
            except Exception as e:
                st.error(f"Generate key gagal: {e}")
        keys = st.session_state.get("generated_keys")
        if keys:
            name, priv, pub = keys
            st.success(f"Pasangan key {name} berhasil dibuat.")
            ca, cb = st.columns(2)
            with ca:
                download_button(f"Download public.pem ({name})", pub, "public.pem", "application/x-pem-file", "key_pub")
            with cb:
                download_button(f"Download private.pem ({name})", priv, "private.pem", "application/x-pem-file", "key_priv")
            st.warning("Jika private key hilang, paket enkripsi dengan public key tersebut tidak bisa dipulihkan. Jangan masukkan private key ke repository publik.")

    st.divider()


def show_comparison_page() -> None:
    st.title("📊 Perbandingan Metode 1 vs Metode 2")
    st.write("Pengujian terkontrol: **gambar, 256-bit session key, nonce, permutation dan diffusion v3 dibuat sama.** Perbedaannya pada pembangkit chaotic map serta pemetaan seed awal yang dibutuhkan masing-masing map.")
    st.caption("RSA/ECC merupakan mekanisme pembentukan/pembungkusan session key yang sama pada kedua metode; benchmark di sini mengisolasi proses enkripsi citra.")
    pic = st.file_uploader("Gambar untuk perbandingan", type=["png", "jpg", "jpeg", "webp", "bmp"], key="compare_input")
    if st.button("Jalankan perbandingan Hénon vs 2DLMUTF", type="primary", disabled=pic is None):
        try:
            with st.spinner("Menjalankan dua metode pada input dan session key yang sama..."):
                original, mode = image_from_bytes(pic.getvalue())
                result = compare_methods(original, os.urandom(32), os.urandom(16))
                st.session_state["comparison"] = (original, mode, result)
        except Exception as exc:
            st.error(f"Perbandingan gagal: {exc}")
    cmp = st.session_state.get("comparison")
    if cmp:
        original, mode, result = cmp
        st.image(original, caption="Gambar asli", width=350)
        c1, c2 = st.columns(2)
        rows = []
        for col,(name,r) in zip((c1,c2),result.items()):
            with col:
                st.subheader(name)
                st.image(r["cipher"], caption="Ciphertext", use_container_width=True)
                st.metric("Exact match setelah dekripsi", "Ya" if r["exact_match"] else "Tidak")
                st.metric("Entropy cipher (bit)",f'{r["entropy_cipher"]:.5f}')
                st.metric("NPCR differential",f'{r["npcr_percent"]:.4f}%')
                st.metric("UACI differential",f'{r["uaci_percent"]:.4f}%')
            cor=r['correlation_cipher']
            rows.append({"Metode":name,"Exact match":r['exact_match'],"Entropy":r['entropy_cipher'],
                         "NPCR (%)":r['npcr_percent'],"UACI (%)":r['uaci_percent'],
                         "Correlation H":cor['horizontal'],"Correlation V":cor['vertical'],
                         "Correlation D":cor['diagonal'],"Encrypt (ms)":r['encrypt_ms'],"Decrypt (ms)":r['decrypt_ms']})
        st.subheader("Ringkasan metrik")
        st.dataframe(rows, hide_index=True, use_container_width=True)
        import csv
        from io import StringIO
        csvio=StringIO(); writer=csv.DictWriter(csvio,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        download_button("Download perbandingan (CSV)",csvio.getvalue().encode('utf-8'),"perbandingan_metode_1_2.csv","text/csv","compare_csv")
        st.info("Nilai yang mendekati acak dan exact recovery tidak otomatis membuktikan keamanan. Untuk kesimpulan ilmiah, ulangi pada banyak gambar/seed dan laporkan mean, standar deviasi, serta waktu eksekusi.")

if page == "📖 Alur Program":
    show_process_page()
elif page == "📊 Bandingkan Metode":
    show_comparison_page()
else:
    show_app_page()

st.divider()
st.caption("Created by Mohamad Idris, S.Si., M.Sc.")
st.caption("Metode 2 — Prototipe penelitian enkripsi citra berbasis 2DLMUTF. Hasil statistik bukan bukti keamanan kriptografi yang telah diaudit.")
