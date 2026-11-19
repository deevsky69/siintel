"""Membaca PDF hasil cetak dan menulis halaman.json: kunci daftar isi -> nomor halaman."""
import json, re, sys
import pypdf

norm = lambda t: re.sub(r"\s+", " ", t).casefold()
pages = [norm(p.extract_text() or "") for p in pypdf.PdfReader(sys.argv[1]).pages]
out, missing = {}, []
for key in json.load(open("isi.json")):
    # Halaman 1 sampul, halaman 2 daftar isi itu sendiri: pencarian mulai halaman 3.
    hit = next((i for i, t in enumerate(pages, 1) if i > 2 and norm(key) in t), None)
    (out.__setitem__(key, hit) if hit else missing.append(key))
json.dump(out, open("halaman.json", "w"), ensure_ascii=False, indent=1)
print(len(out), "terisi; tidak ditemukan:", missing)
