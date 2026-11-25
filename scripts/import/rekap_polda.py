#!/usr/bin/env python3
"""Impor rekap kriminalitas Polda Metro Jaya per Polres (Pusiknas) → SIGAP.

    cd apps/api && uv run --group analysis python ../../scripts/import/rekap_polda.py BERKAS.xlsx
    …/rekap_polda.py BERKAS.xlsx --kirim https://alamat-sigap --pengguna demo.admin

Tanpa `--kirim` skrip hanya membaca, memvalidasi, dan mencetak ringkasan (tidak ada yang
ditulis ke mana pun). Dengan `--kirim` paketnya dikirim ke `PUT /api/v1/polda/recap` atas nama
akun yang memegang `config:manage`; kata sandi dibaca dari variabel lingkungan `SANDI` atau
ditanyakan — tidak pernah dari argumen, supaya tidak tertinggal di riwayat shell.

Pipeline CLAUDE.md §18: berkas sumber → validasi → pemetaan → basis data (lewat API, yang
memvalidasi ulang dan mencatat audit). Tidak ada anonimisasi karena sumbernya agregat per
satuan: tidak memuat nama orang, nomor laporan, alamat, atau identitas apa pun — dan skrip
berhenti bila menemukan lembar yang tidak dikenalnya, alih-alih mengabaikannya.

Yang divalidasi sebelum apa pun dikirim (satu selisih menggagalkan impor):
- jumlah per satuan = baris JUMLAH, untuk CT, CC, dan tiap jenis 3C, tiap tahun;
- curat + curas + curanmor = jumlah 3C tiap satuan;
- jumlah per bulan = jumlah setahun;
- lembar Ringkasan = baris JUMLAH pada Tabel 1 dan Tabel 2.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import openpyxl

WIB = timezone(timedelta(hours=7))
SHEETS = {
    "Keterangan", "Ringkasan", "Tabel 1 3C per Polres", "Tabel 2 Keseluruhan per Polres",
    "3C per Polres dan Jenis", "Per Jenis 3C", "Per Bulan", "Jenis Terbanyak",
}  # fmt: skip
MONTHS = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September",
    "Oktober", "November", "Desember",
]  # fmt: skip
TYPES = {"Curat": "curat", "Curas": "curas", "Curanmor": "curanmor"}


class Gagal(Exception):
    pass


def rows(book: Any, title: str) -> list[list[Any]]:
    return [list(row) for row in book[title].iter_rows(values_only=True)]


def number(value: Any) -> int:
    if value in (None, "", "-"):
        return 0
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != int(value):
        raise Gagal(f"bukan bilangan bulat: {value!r}")
    return int(value)


def year_of(header: Any) -> str | None:
    found = re.search(r"(20\d\d)", str(header or ""))
    return found.group(1) if found else None


def header_row(table: list[list[Any]], first: str) -> int:
    for index, row in enumerate(table):
        if row and str(row[0] or "").strip() == first:
            return index
    raise Gagal(f"baris kepala '{first}' tidak ditemukan")


def unit_table(
    table: list[list[Any]],
) -> tuple[dict[str, dict[str, dict[str, int]]], dict[str, Any], dict[str, float | None]]:
    """Tabel 1 / Tabel 2: per satuan → tahun → {ct, cc}; baris JUMLAH; perubahan periode setara."""
    start = header_row(table, "No")
    head = table[start]
    columns: dict[tuple[str, str], int] = {}
    change = None
    for position, cell in enumerate(head):
        text = str(cell or "")
        year = year_of(text)
        if text.startswith("CT") and year:
            columns[(year, "ct")] = position
        elif text.startswith("CC") and year:
            columns[(year, "cc")] = position
        elif "perubahan" in text:
            change = position
    units: dict[str, dict[str, dict[str, int]]] = {}
    changes: dict[str, float | None] = {}
    total: dict[str, Any] = {}
    for row in table[start + 1 :]:
        name = str(row[1] or "").strip() if len(row) > 1 else ""
        if not name:
            continue
        values = {year: {"ct": 0, "cc": 0} for year in sorted({year for year, _ in columns})}
        for (year, key), position in columns.items():
            values[year][key] = number(row[position])
        if name.upper().startswith("JUMLAH"):
            total = values
            break
        units[name] = values
        raw = row[change] if change is not None else None
        changes[name] = float(raw) if isinstance(raw, (int, float)) else None
    if not total:
        raise Gagal("baris JUMLAH tidak ditemukan")
    return units, total, changes


def baca(path: Path) -> dict[str, Any]:
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    unknown = set(book.sheetnames) - SHEETS
    missing = SHEETS - set(book.sheetnames)
    if unknown or missing:
        raise Gagal(
            f"susunan lembar berubah — tidak dikenal: {sorted(unknown)}; hilang: {sorted(missing)}"
        )

    note = " ".join(str(cell) for row in rows(book, "Keterangan") for cell in row if cell)
    found = re.search(r"posisi data (\d{1,2}) (\w+) (20\d\d) pukul (\d{1,2})\.(\d{2})", note)
    if not found:
        raise Gagal("posisi data tidak terbaca pada lembar Keterangan")
    day, month_name, year, hour, minute = found.groups()
    posisi = datetime(
        int(year), MONTHS.index(month_name) + 1, int(day), int(hour), int(minute), tzinfo=WIB
    )

    c3_units, c3_total, c3_change = unit_table(rows(book, "Tabel 1 3C per Polres"))
    all_units, all_total, all_change = unit_table(rows(book, "Tabel 2 Keseluruhan per Polres"))
    years = sorted(all_total)

    # Rincian jenis 3C per satuan.
    table = rows(book, "3C per Polres dan Jenis")
    start = header_row(table, "No")
    type_columns = {
        (year_of(cell), TYPES[str(cell).split()[0]]): position
        for position, cell in enumerate(table[start])
        if str(cell or "").split()[:1] and str(cell).split()[0] in TYPES
    }
    by_type: dict[str, dict[str, dict[str, int]]] = {}
    type_total: dict[str, dict[str, int]] = {}
    for row in table[start + 1 :]:
        name = str(row[1] or "").strip() if len(row) > 1 else ""
        if not name:
            continue
        values: dict[str, dict[str, int]] = {year: {} for year in years}
        for (year, key), position in type_columns.items():
            values[str(year)][key] = number(row[position])
        if name.upper().startswith("JUMLAH"):
            type_total = values
            break
        by_type[name] = values

    units = []
    for name, overall in all_units.items():
        if name not in by_type:
            raise Gagal(f"{name}: tidak ada pada lembar jenis 3C")
        c3 = {}
        for year in years:
            kinds = by_type[name][year]
            ct = sum(kinds.values())
            listed = c3_units.get(name, {}).get(year)
            if listed and listed["ct"] != ct:
                raise Gagal(f"{name} {year}: Tabel 1 ({listed['ct']}) ≠ rincian jenis ({ct})")
            c3[year] = {"ct": ct, "cc": listed["cc"] if listed else 0, **kinds}
        units.append(
            {
                "name": name,
                "kind": "POLRES" if name.startswith(("Polres", "Polresta")) else "SATKER",
                "overall": overall,
                "c3": c3,
                "change_overall": all_change.get(name),
                "change_c3": c3_change.get(name),
            }
        )
    stray = set(c3_units) - set(all_units)
    if stray:
        raise Gagal(f"satuan pada Tabel 1 tanpa padanan di Tabel 2: {sorted(stray)}")

    totals = {
        "overall": all_total,
        "c3": {year: {**c3_total[year], **type_total[year]} for year in years},
    }

    # Ringkasan: harus sama dengan baris JUMLAH; memuat juga periode setara.
    summary = rows(book, "Ringkasan")
    start = header_row(summary, "Tahun")
    for row in summary[start + 1 : start + 1 + len(years)]:
        year = year_of(row[0])
        if year is None:
            break
        if (number(row[1]), number(row[2]), number(row[5]), number(row[6])) != (
            all_total[year]["ct"], all_total[year]["cc"],
            c3_total[year]["ct"], c3_total[year]["cc"],
        ):  # fmt: skip
            raise Gagal(f"Ringkasan {year} ≠ baris JUMLAH Tabel 1/Tabel 2")
    equal = None
    try:
        start = header_row(summary, "Periode")
        label = re.search(r"\((.+?)\)", str(summary[start + 1][0]))
        equal = {"label": label.group(1) if label else "periode setara", "overall": {}, "c3": {}}
        for row in summary[start + 1 :]:
            year = year_of(row[0]) if row and row[0] else None
            if year is None or len(row) < 6:
                break
            equal["overall"][year] = {"ct": number(row[1]), "cc": number(row[2])}
            equal["c3"][year] = {"ct": number(row[4]), "cc": number(row[5])}
    except Gagal:
        equal = None

    # Per bulan.
    table = rows(book, "Per Bulan")
    start = header_row(table, "Bulan")
    head = table[start]
    monthly = []
    for row in table[start + 1 :]:
        name = str(row[0] or "").strip()
        if name not in MONTHS:
            continue
        entry: dict[str, Any] = {"month": MONTHS.index(name) + 1, "overall": {}, "c3": {}}
        for position, cell in enumerate(head[1:], start=1):
            year = year_of(cell)
            if year is None or position >= len(row) or row[position] is None:
                continue
            entry["c3" if str(cell).startswith("3C") else "overall"][year] = number(row[position])
        monthly.append(entry)

    # Bentuk penyelesaian 3C.
    table = rows(book, "Per Jenis 3C")
    settlements = []
    try:
        start = header_row(table, "Bentuk penyelesaian")
        head = table[start]
        for row in table[start + 1 :]:
            form = str(row[0] or "").strip()
            if not form or form.upper().startswith(("JUMLAH", "CONFIDENTIAL")):
                break
            settlements.append(
                {
                    "form": form,
                    "counts": {
                        year_of(head[position]): number(row[position])
                        for position in range(1, len(head))
                        if year_of(head[position]) and position < len(row)
                    },
                }
            )
    except Gagal:
        pass

    # Dua puluh jenis terbanyak.
    table = rows(book, "Jenis Terbanyak")
    start = header_row(table, "No")
    head = table[start]
    top: dict[str, list[dict[str, Any]]] = {}
    for row in table[start + 1 :]:
        if not isinstance(row[0], (int, float)):
            continue
        for position in range(1, len(head) - 1, 2):
            year = year_of(head[position])
            if year and row[position]:
                top.setdefault(year, []).append(
                    {
                        "rank": int(row[0]),
                        "name": str(row[position]).strip(),
                        "ct": number(row[position + 1]),
                    }
                )

    until = re.search(r"s\.d\. (\d{1,2}) (\w+) (20\d\d)", note)
    current_until = (
        date(int(until.group(3)), MONTHS.index(until.group(2)) + 1, int(until.group(1)))
        if until
        else posisi.date()
    )
    return {
        "position_at": posisi.isoformat(),
        "source": f"Pusiknas Bareskrim Polri — {path.name}",
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "years": [int(year) for year in years],
        "current_year": current_until.year,
        "current_until": current_until.isoformat(),
        "units": units,
        "totals": totals,
        "equal_period": equal,
        "monthly": monthly,
        "settlements": settlements,
        "top_types": top,
    }


def periksa(paket: dict[str, Any]) -> list[str]:
    """Pemeriksaan yang sama dengan API (`routers/polda.check`), dijalankan sebelum mengirim."""
    masalah: list[str] = []
    for year in (str(y) for y in paket["years"]):
        for scope, keys in (
            ("overall", ("ct", "cc")),
            ("c3", ("ct", "cc", "curat", "curas", "curanmor")),
        ):
            for key in keys:
                got = sum(unit[scope][year][key] for unit in paket["units"])
                expected = paket["totals"][scope][year][key]
                if got != expected:
                    masalah.append(f"{year} {scope}.{key}: per satuan {got} ≠ JUMLAH {expected}")
            got = sum(month[scope].get(year, 0) for month in paket["monthly"])
            if paket["monthly"] and got != paket["totals"][scope][year]["ct"]:
                masalah.append(
                    f"{year} {scope}: per bulan {got} ≠ setahun "
                    f"{paket['totals'][scope][year]['ct']}"
                )
    return masalah


def kirim(base: str, pengguna: str, sandi: str, paket: dict[str, Any]) -> dict[str, Any]:
    def call(
        method: str, path: str, body: dict[str, Any], token: str | None = None
    ) -> dict[str, Any]:
        request = urllib.request.Request(  # noqa: S310 — skema diperiksa di bawah
            base.rstrip("/") + "/api/v1" + path,
            data=json.dumps(body).encode(),
            method=method,
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {token}"} if token else {}),
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
                return json.load(response)  # type: ignore[no-any-return]
        except urllib.error.HTTPError as error:
            raise Gagal(f"{method} {path} → {error.code}: {error.read().decode()[:400]}") from error

    if not base.startswith(("https://", "http://")):
        raise Gagal("--kirim harus berupa alamat http(s)")
    token = call("POST", "/auth/login", {"username": pengguna, "password": sandi})["access_token"]
    return call("PUT", "/polda/recap", paket, token)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("berkas", type=Path)
    parser.add_argument("--kirim", metavar="ALAMAT", help="alamat SIGAP, mis. https://sigap.contoh")
    parser.add_argument("--pengguna", help="akun pemegang config:manage")
    parser.add_argument("--simpan", type=Path, help="tulis paket JSON ke berkas ini")
    args = parser.parse_args()
    try:
        paket = baca(args.berkas)
        masalah = periksa(paket)
        if masalah:
            raise Gagal("jumlah tidak cocok:\n  " + "\n  ".join(masalah))
        polres = [unit for unit in paket["units"] if unit["kind"] == "POLRES"]
        print(
            f"posisi data {paket['position_at']}; {len(polres)} Polres, "
            f"{len(paket['units']) - len(polres)} satuan kerja Polda"
        )
        for year in paket["years"]:
            t = paket["totals"]
            print(
                f"  {year}: keseluruhan CT {t['overall'][str(year)]['ct']} "
                f"CC {t['overall'][str(year)]['cc']}; 3C CT {t['c3'][str(year)]['ct']} "
                f"CC {t['c3'][str(year)]['cc']}"
            )
        print("seluruh jumlah cocok dengan baris JUMLAH sumber")
        if args.simpan:
            args.simpan.write_text(json.dumps(paket, ensure_ascii=False, indent=1))
            print("paket ditulis ke", args.simpan)
        if args.kirim:
            if not args.pengguna:
                raise Gagal("--kirim memerlukan --pengguna")
            sandi = os.environ.get("SANDI") or getpass.getpass(f"Kata sandi {args.pengguna}: ")
            hasil = kirim(args.kirim, args.pengguna, sandi, paket)
            print("terkirim:", hasil)
    except Gagal as error:
        print("GAGAL:", error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
