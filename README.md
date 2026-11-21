# Metode 2 — 2DLMUTF + RSA/ECC (Streamlit + CLI)

**Created by Mohamad Idris, S.Si., M.Sc.**

Prototipe penelitian enkripsi citra berbasis **2D Logistic Map with Unit Transfer Function and Modulus (2DLMUTF)**. Paket ini dapat dijalankan sebagai aplikasi Streamlit pada VPS Ubuntu (Docker) dan sebagai aplikasi CLI Python untuk eksperimen.

**Referensi map:** Ahmad, R. dkk. (2025), *2D logistic map with unit transfer function and modulus operation based pseudorandom number generation for image encryption*, Scientific Reports 15, 19330. https://doi.org/10.1038/s41598-025-04702-0

> **Penting mengenai metode ilmiah:** Artikel asli menggunakan 2DLMUTF untuk menghasilkan deret pseudorandom dan S-box. **Kode ini merupakan ADAPTASI**: persamaan map 2DLMUTF dari artikel digunakan sebagai sumber chaos untuk permutation dan diffusion dua ronde yang dipertahankan dari Metode 1. RSA-3072 OAEP-SHA256 / ECC-X25519 membungkus atau membentuk session key. Kode ini bukan implementasi identik algoritma enkripsi citra artikel tersebut dan belum diaudit secara kriptografi.

## 1. Fitur

| Menu / fitur | Kegunaan |
|---|---|
| 🖼️ Aplikasi → Demo satu klik | Upload gambar, pilih RSA/ECC, buat key demo, encrypt, decrypt, metrik, dan unduh hasil |
| 🔒 Enkripsi file | Upload gambar + public.pem, lalu unduh `cipher.png` dan `metadata.json` dalam ZIP |
| 🔓 Dekripsi file | Upload ZIP + private.pem dari pasangan yang sama; dapat gambar kembali |
| 🗝️ Buat kunci | Generate RSA-3072 atau ECC-X25519 dan unduh pasangan PEM |
| 📖 Alur Program | Flowchart enkripsi dan dekripsi, persamaan 2DLMUTF, penjelasan metrik |
| 📊 Bandingkan Metode | Jalankan Metode 1 Hénon vs Metode 2 2DLMUTF pada gambar, key dan nonce sama; tampilkan ciphertext/hasil statistik/timing dan CSV |
| CLI + eksperimen | keygen, encrypt, decrypt, evaluate, differential, differential-sweep, robustness, key-sensitivity, benchmark, batch-benchmark |
| `compare_cli.py` | Multi-trial perbandingan Hénon vs 2DLMUTF dengan `trials.csv`, `summary.csv`, `summary.json` |

## 2. Cara menjalankan di VPS Ubuntu (Docker)

**Kompatibel dengan aplikasi Metode 1 yang sudah berjalan di port 8501.** Metode 2 memakai **8502 di host VPS**, container terpisah. Jangan menimpa folder Metode 1.

Prasyarat: Docker Engine, Docker Compose, dan unzip tersedia (`docker compose version`).

### Dari laptop Windows (PowerShell)

```powershell
scp Chaos_Image_Method2_2DLMUTF_Streamlit_VPS.zip ubuntu@IP_VPS:~/
```

Ganti `IP_VPS` dengan IP sebenarnya, `ubuntu` dengan user SSH yang valid.

### Di VPS

```bash
cd ~
unzip Chaos_Image_Method2_2DLMUTF_Streamlit_VPS.zip
cd chaos-image-encryption-method2-web
cp .env.example .env
nano .env
```

Set **password panjang yang baru**, misalnya:

```ini
APP_PASSWORD=PASSWORD_RANDOM_PANJANG_UNIK
```

`APP_PASSWORD` tidak boleh menggunakan nilai default. Jangan commit `.env` ke GitHub.

```bash
chmod 600 .env
docker compose up -d --build
docker compose ps
docker compose logs --tail=60
```

Output port yang diharapkan:

```text
127.0.0.1:8502->8501/tcp
```

Docker menjalankan service internal di port 8501, tetapi port **8502 hanya bisa diakses lokal dari host VPS**. Metode 1 tetap di port 8501. Jika sedang memakai `docker compose` Metode 1, jalankan `docker compose` untuk Metode 2 dari **folder Metode 2** ini.

### Buka website dari laptop tanpa domain

Di PowerShell (buat SSH baru dan biarkan terbuka):

```powershell
ssh -L 8502:127.0.0.1:8502 ubuntu@IP_VPS
```

Buka `http://localhost:8502` di browser laptop. Masukkan `APP_PASSWORD`.

Jika port 8502 lokal laptop sudah dipakai:

```powershell
ssh -L 18502:127.0.0.1:8502 ubuntu@IP_VPS
```

Kemudian buka `http://localhost:18502`.

**Untuk dosen mengakses dari luar jaringan:** gunakan HTTPS melalui reverse proxy atau HTTPS tunnel berautentikasi. Jangan sembarang expose `8502` via HTTP publik karena ada fitur upload private key. Jika kamu sedang memakai HTTP publik untuk Metode 1, batasi hanya data/key demo. Dokumen ini tidak menyertakan langkah membuka firewall publik secara default.

### Perubahan kode, log dan stop

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f --tail=100
docker compose down
```

## 3. Cara mencoba di browser (untuk dosen)

1. Masuk ke web memakai password.
2. Buka **🖼️ Aplikasi → Demo satu klik**.
3. Upload gambar `.png` atau `.jpg`, lalu pilih **RSA** atau **ECC**.
4. Klik **Jalankan demo enkripsi + dekripsi**.
5. Bandingkan gambar asli, terenkripsi, dan terdekripsi. Lihat exact match, PSNR, SSIM, entropy, korelasi serta histogram.
6. Klik **Jalankan pengujian tambahan** untuk differential test 1-bit, key sensitivity dan robustness ringan.
7. Download ZIP demo jika diperlukan. Private key demo diunduh **terpisah**, bukan disertakan di ZIP.
8. Buka **📖 Alur Program** untuk flowchart/rumus, atau **📊 Bandingkan Metode** untuk membandingkan dengan Hénon dari Metode 1.

**Tentang key:** demo satu klik membangkitkan key secara otomatis. Untuk alur manual, penerima membuat key di tab Buat Kunci → pemberi gambar mengenkripsi dengan `public.pem` → penerima mendekripsi dengan `private.pem`. Jangan menggunakan atau membagikan private key produksi.

## 4. Cara menjalankan Python tanpa Docker

Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export APP_PASSWORD='PASSWORD_RANDOM_PANJANG_UNIK'
streamlit run streamlit_app.py --server.address=127.0.0.1 --server.port=8502
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:APP_PASSWORD = 'PASSWORD_RANDOM_PANJANG_UNIK'
streamlit run streamlit_app.py --server.port=8502
```

## 5. CLI: generate key, encrypt, decrypt dan evaluasi

Jalankan dari folder project pada terminal dengan Python dan requirements sudah terinstal.

### RSA

```bash
python main.py keygen --type rsa --out-dir keys/rsa
python main.py encrypt --image tes_synth.png --crypto rsa --public-key keys/rsa/public.pem --out results/cipher_rsa.png
python main.py decrypt --image results/cipher_rsa.png --metadata results/cipher_rsa.json --private-key keys/rsa/private.pem --out results/decrypted_rsa.png
python main.py evaluate --original tes_synth.png --encrypted results/cipher_rsa.png --decrypted results/decrypted_rsa.png --out-dir results/evaluation_rsa
```

### ECC X25519

```bash
python main.py keygen --type ecc --out-dir keys/ecc
python main.py encrypt --image tes_synth.png --crypto ecc --public-key keys/ecc/public.pem --out results/cipher_ecc.png
python main.py decrypt --image results/cipher_ecc.png --metadata results/cipher_ecc.json --private-key keys/ecc/private.pem --out results/decrypted_ecc.png
python main.py evaluate --original tes_synth.png --encrypted results/cipher_ecc.png --decrypted results/decrypted_ecc.png --out-dir results/evaluation_ecc
```

### Eksperimen individual dan batch

```bash
python main.py differential --image tes_synth.png --out-dir results/differential
python main.py differential-sweep --image tes_synth.png --trials 20 --out-dir results/differential_20
python main.py key-sensitivity --image tes_synth.png --trials 20 --out-dir results/key_sensitivity
python main.py robustness --image tes_synth.png --crypto rsa --out-dir results/robustness
python main.py benchmark --image tes_synth.png --out-dir results/benchmark
python main.py batch-benchmark --input-dir data --out-dir results/batch --crypto all
```

Folder `data/` kosong secara default. Isi dengan dataset lokal penelitian kalau mau menguji banyak citra. Eksperimen pertama bisa memakai file `tes_synth.png` yang sudah disertakan.

### Perbandingan multi-trial Metode 1 vs 2 (lebih relevan untuk laporan)

```bash
python compare_cli.py --image tes_synth.png --trials 20 --out-dir results/perbandingan
```

Keluaran:

- `results/perbandingan/trials.csv`: setiap trial untuk masing-masing metode.
- `results/perbandingan/summary.csv`: mean dan population standard deviation tiap metrik.
- `results/perbandingan/summary.json`: ringkasan yang dapat dibaca program.

Perbandingan memakai **gambar, session key 32 byte, nonce 16 byte dan diffusion v3 yang sama**. Seed dipetakan ke domain chaos masing-masing untuk menjamin kondisi awal valid. Timing yang dilaporkan adalah eksperimen lokal pada mesin yang digunakan, bukan patokan universal.

## 6. Rumus dan parameter

Sesuai persamaan (5)–(6) dari Ahmad dkk. (2025):

```text
x[n+1] = mod((r1 + x[n]*(1-x[n])) / (y[n]*(1-y[n])), 1)
y[n+1] = mod((r2 + y[n]*(1-y[n])) / (x[n]*(1-x[n+1])), 1)
```

Parameter aplikasi: `r1=4.0`, `r2=3.8` (`r2=r1-0.2`), `burn_in=1000`; seed `x0`, `y0` diturunkan dengan HKDF-SHA256 dari session key, nonce, ukuran citra, dan label domain. Nilai sangat dekat 0/1 atau penyebut yang terlalu kecil diberi pelindung `epsilon=1e-12` agar tidak membagi nol dalam floating-point. **Safeguard ini merupakan keputusan implementasi dan perlu dilaporkan**, bukan mengklaim persis sama dengan implementasi MATLAB jurnal.

Citra 8-bit RGB/grayscale → permutation pixel berdasarkan `argsort` deret X → nonlinear diffusion v3 dua ronde. Dekripsi membalik operasi dengan key/nonce yang sama. Info rumus lebih lengkap: `METODOLOGI_DAN_RUMUS.md`.

## 7. Verifikasi source code

```bash
python -m pytest -q
python -m compileall -q .
```

Pengujian mencakup generator 2DLMUTF (persamaan pertama vs hitungan manual, determinisme, domain nilai), enkripsi/dekripsi grayscale/RGB, RSA/ECC, metrik, robustness, key sensitivity, ZIP upload/download, dan perbandingan metode.

## 8. Struktur folder

```text
streamlit_app.py                     UI 3 halaman: aplikasi, alur, perbandingan
web_adapter.py                       penghubung UI dengan encryption/decryption di RAM
main.py                              CLI Metode 2
compare_cli.py                       uji multi-trial perbandingan Metode 1 vs 2
src/chaos_image_encryption/chaos/logistic_utf.py    persamaan 2DLMUTF
src/chaos_image_encryption/comparison.py            Hénon referensi Metode 1
src/chaos_image_encryption/cipher/core.py           permutation + diffusion v3
tests/                               unit dan integration tests
assets/                              flowchart Metode 2
Dockerfile / docker-compose.yml      deploy VPS Ubuntu
.env.example                         contoh konfigurasi password
METODOLOGI_DAN_RUMUS.md              dokumentasi algoritma dan metrik
```

## 9. Batasan dan keamanan

- **Research prototype, bukan sistem keamanan yang terbukti aman.** Hasil entropy, NPCR, UACI dan histogram tidak menggantikan audit keamanan / pembuktian CCA/CPA.
- **Tidak ada authenticated encryption atau integrity tag** pada ciphertext. Bila ciphertext atau metadata dimodifikasi, program tidak bisa menjamin deteksi manipulasi. Jangan menganggap setara AES-GCM/ChaCha20-Poly1305.
- Input gambar maksimal **2 juta pixel**, file upload maksimal **15 MB**, citra `uint8` grayscale dan RGB. Gambar RGBA/P/CMYK dinormalisasi; hasil exact berarti pixel setelah konversi, bukan byte file original.
- Jangan menyimpan ciphertext menggunakan JPEG; gunakan PNG/ZIP agar nilai pixel cipher tidak rusak.
- Upload diproses di memori aplikasi, tetapi private key diproses di **RAM server VPS** sehingga jangan menggunakan kunci sensitif asli. `APP_PASSWORD` hanya password bersama, bukan mekanisme akun pengguna.
- Hindari akses publik HTTP tanpa TLS. Gunakan private SSH tunnel atau HTTPS tunnel/reverse proxy dengan autentikasi jika diakses dari luar.
- Jika membandingkan metode, ulangi pada **banyak gambar/seed**, catat resolusi/dataset/waktu, dan jangan menyimpulkan hasil umum dari satu gambar atau 1–3 trial.
