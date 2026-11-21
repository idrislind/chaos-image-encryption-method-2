# Metodologi dan Rumus — Metode 2 (2DLMUTF)

**Created by Mohamad Idris, S.Si., M.Sc.**

## Sumber ilmiah

Ahmad, R., Said, G., Flah, A., dkk. (2025), *2D logistic map with unit transfer function and modulus operation based pseudorandom number generation for image encryption*. *Scientific Reports*, 15, 19330. DOI: https://doi.org/10.1038/s41598-025-04702-0

**Batas cakupan:** Persamaan chaotic map (5)–(6) mengacu pada artikel tersebut. Artikel aslinya membangun S-box dari deret 2DLMUTF. Penelitian ini mengadaptasi generator chaos untuk kerangka RSA/ECC, permutation, dan nonlinear diffusion v3 yang sama dengan Metode 1, sehingga dapat menguji pengaruh perubahan *map* secara terkontrol. Tidak dinyatakan sebagai replikasi penuh cipher artikel.

## Alur Metode 2

1. Baca gambar (L / RGB, setiap channel 8-bit).
2. Persiapkan session key 256-bit: RSA-3072 OAEP mengenkripsi session key random atau ECC X25519 ECDH + HKDF-SHA256 membentuk session key dari shared secret.
3. Buat nonce 16-byte dan turunkan parameter awal dengan HKDF-SHA256 dari session key, nonce, shape citra, dan domain (`permutation`, `diffusion-1`, `diffusion-2`).
4. Bangkitkan deret chaos dengan 2DLMUTF; buang 1000 iterasi awal (*burn-in*).
5. Permutasikan posisi piksel berdasarkan `argsort` deret X, dengan kanal RGB tetap bersama per piksel.
6. Ubah nilai byte menggunakan nonlinear diffusion v3 dua ronde. Hasil `cipher.png` disimpan dengan metadata (nonce, ukuran/mode, jenis backend, wrapped session key/ephemeral key), tanpa private key.
7. Pada dekripsi, recover session key menggunakan private key, hasilkan lagi deret chaos, inverse diffusion, dan inverse permutation.

## 2DLMUTF dari Ahmad dkk. (2025)

Persamaan (5):

```text
x[n+1] = ((r1 + x[n]*(1-x[n])) / (y[n]*(1-y[n]))) mod 1
```

Persamaan (6):

```text
y[n+1] = ((r2 + y[n]*(1-y[n])) / (x[n]*(1-x[n+1]))) mod 1
```

Pada artikel, dipakai `r1 = 4.0`, `r2 = 3.8`, dengan contoh `x0 = 0.235` dan `y0 = 0.350`. Di program, nilai awal **bukan konstanta global**: diturunkan dari 256-bit session key dan 16-byte nonce per domain agar setiap enkripsi punya kondisi awal berbeda. Nilai awal dipetakan ke `(0.1, 0.9)`. `burn_in=1000`.

Implementasi menggunakan Python `float64` dan `epsilon=1e-12` untuk membatasi penyebut dan menghindari kondisi 0/1 sesudah operasi modulus akibat rounding. Ini pengaman numerik, yang menyebabkan implementasi **tidak persis identik** dengan lintasan floating-point tanpa safeguard dan harus dinyatakan dalam laporan.

**Penting:** float64 chaotic map dan bytes kuantisasi secara numerik sensitif terhadap detail implementasi; untuk interoperabilitas, pakai versi source/config yang sama pada enkripsi dan dekripsi.

## Permutation

Jika `P` adalah matriks piksel citra dan `X` deret chaotic sepanjang `H × W`:

```text
perm = argsort(X)
P_perm = P[perm]
```

Permutasi diterapkan ke piksel (bukan mengacak kanal RGB secara terpisah). Untuk dekripsi, digunakan `inverse_permutation`.

## Diffusion v3

Citra hasil permutation diratakan menjadi urutan byte `p_i`, kemudian pada setiap ronde dilakukan substitusi byte reversibel dan *feedback* nonlinear. Ringkasan salah satu komponen:

```text
q_i = SBOX[p_i XOR k1_i]
f_i = (a_i*f_(i-1) + q_i + k2_i) mod 256
```

Koefisien `a_i` selalu ganjil sehingga memiliki invers modulo 256. Algoritma lengkap memiliki substitusi tambahan, jalur balik arah, dan **dua ronde** v3. Implementasi detail berada di `src/chaos_image_encryption/chaos/diffusion.py`. S-box tetap adalah fixed AES S-box sebagai komponen nonlinear; **bukan berarti cipher ini adalah AES**. Diffusion v3 dipertahankan sama dengan Metode 1 untuk perbandingan yang lebih terkontrol.

## Evaluasi hasil

- **Exact match, MSE, PSNR, SSIM**: perbandingan citra asli vs dekripsi untuk menguji reversibilitas.
- **Entropy, histogram, adjacent pixel correlation**: statistik citra terenkripsi.
- **Differential NPCR/UACI**: ubah **1 bit plaintext**, gunakan key + nonce sama, bandingkan kedua ciphertext.
- **Key sensitivity NPCR/UACI**: plaintext + nonce sama, ubah **1 bit session key**, bandingkan ciphertext dan kesalahan dekripsi dengan kunci salah.
- **Robustness**: serang ciphertext dengan noise, block erasure atau recompress JPEG; bandingkan hasil dekripsi dengan asli. Robustness tidak harus sempurna untuk skema ciphertext yang bersifat difusi kuat.
- **Benchmark**: kecepatan enkripsi/dekripsi, throughput, memori, dan perbandingan RSA/ECC.

**NPCR dan UACI pada differential vs key sensitivity memakai rumus metrik yang sama, tetapi variabel yang diubah berbeda.** Acuan statistik yang lazim untuk dua ciphertext 8-bit yang dekat independen-acak adalah NPCR ≈ 99,6094% dan UACI ≈ 33,4635%; kedekatan ke acuan ini bukan bukti kuat keamanan.

## Cara membandingkan Metode 1 dan 2 secara adil

Di `comparison.py`, Metode 1 Hénon dipertahankan seperti core Milestone 4; Metode 2 mengganti generator menjadi 2DLMUTF. Gambar, key, nonce, permutation, diffusion v3, dan perangkat evaluasi dibuat sama. Perbedaan karakter map membutuhkan pemetaan seed ke rentang valid yang berbeda. Jalankan:

```bash
python compare_cli.py --image tes_synth.png --trials 20 --out-dir results/perbandingan
```

Untuk hasil akademis, jalankan pada banyak gambar L/RGB dari dataset berizin, resolusi yang konsisten, ulangi per gambar/key/nonce, lalu analisis mean, standard deviation dan data mentah. Untuk perbandingan runtime, gunakan lingkungan CPU/proses yang seragam. Uji randomness dari deret map secara terpisah (uniformity, autocorrelation, entropy, NIST STS jika relevan) sebelum mengklaim sifat PRNG.

## Catatan keamanan

Penggunaan RSA/ECC di sini membentuk/membungkus session key saja; tidak membuktikan bahwa primitive chaotic image encryption menghasilkan keamanan semantik. Keluaran cipher tidak diautentikasi. Pakai ini sebagai prototipe riset, bukan untuk kerahasiaan data pribadi/industri.
