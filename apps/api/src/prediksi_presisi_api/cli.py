"""Perintah administrasi (TASK 050).

`set-password` menetapkan kredensial akun **di server**, bukan lewat kode. Password
tidak pernah masuk repository, tidak pernah ditulis ke berkas seed, dan tidak muncul
sebagai argumen perintah — dimasukkan lewat prompt tersembunyi.

`backtest` menjalankan evaluasi mundur (`services/backtest.py`) dan menulis
`predictions` (VALIDATED) + `prediction_actual` untuk satu rentang hari — pekerjaan batch
yang tidak punya tombol di layar, dan memang tidak perlu punya.

Contoh:

    pnpm user:password -- demo.pimpinan
    uv run python -m prediksi_presisi_api.cli backtest --dari 2026-01-01 --sampai 2026-09-28
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from datetime import date

from sqlalchemy import select

from .db import get_session_factory
from .models import User
from .security.passwords import hash_password
from .services import backtest as backtesting

#: Diturunkan dari 12 ke 10 pada 7 Oktober 2026 atas keputusan pemilik proyek untuk
#: kata sandi peragaan (`A-12345678`). Pengaman teknis, bukan kebijakan resmi (U-05);
#: naikkan kembali sebelum pilot.
MINIMUM_LENGTH = 10


def set_password(username: str, password: str | None = None) -> int:
    with get_session_factory()() as session, session.begin():
        user = session.scalar(select(User).where(User.username == username))
        if user is None:
            print(f"Pengguna '{username}' tidak ditemukan.", file=sys.stderr)
            return 1

        if password is None:
            password = getpass.getpass(f"Password baru untuk {username}: ")
            confirmation = getpass.getpass("Ulangi password: ")
            if password != confirmation:
                print("Password tidak sama.", file=sys.stderr)
                return 1

        if len(password) < MINIMUM_LENGTH:
            # Panjang minimum ini adalah pengaman teknis, bukan kebijakan resmi:
            # kebijakan password organisasi masih menunggu keputusan (U-05).
            print(
                f"Password minimal {MINIMUM_LENGTH} karakter. "
                "Kebijakan resmi menunggu penetapan pemilik proyek (U-05).",
                file=sys.stderr,
            )
            return 1

        user.password_hash = hash_password(password)
        user.must_change_password = False

    print(f"Password untuk '{username}' diperbarui.")
    return 0


def lock_user(username: str) -> int:
    """Mengunci akun: tidak dapat masuk, tetapi barisnya tetap ada.

    Dihapus tidak mungkin dan tidak diinginkan: jejak audit merujuk ke akun ini
    (append-only), dan tindakan yang pernah dicatatnya harus tetap tertelusur ke pelakunya.
    """
    with get_session_factory()() as session, session.begin():
        user = session.scalar(select(User).where(User.username == username))
        if user is None:
            print(f"Pengguna '{username}' tidak ditemukan.", file=sys.stderr)
            return 1
        user.password_hash = "!"  # noqa: S105 — penanda terkunci, bukan hash
        user.status = "INACTIVE"
    print(f"Akun '{username}' dikunci.")
    return 0


def list_users() -> int:
    with get_session_factory()() as session:
        users = session.scalars(select(User).order_by(User.code)).all()
        print(f"{'CODE':<10} {'USERNAME':<22} {'ROLE':<16} {'STATUS':<10} KREDENSIAL")
        for user in users:
            state = "terkunci" if user.password_hash == "!" else "aktif"  # noqa: S105
            print(
                f"{user.code:<10} {user.username:<22} {user.role.role_name:<16} "
                f"{user.status:<10} {state}"
            )
    return 0


def run_backtest(start: date, end: date, horizon: str, dry_run: bool) -> int:
    with get_session_factory()() as session:
        try:
            summary = backtesting.run_backtest(
                session, start, end, horizon=horizon.upper(), write=not dry_run
            )
        except backtesting.BacktestError as error:
            print(str(error), file=sys.stderr)
            return 1
        if dry_run:
            session.rollback()
        else:
            session.commit()
    print(json.dumps(summary.as_dict(), ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="predpol", description="Administrasi PREDIKSI PRESISI")
    sub = parser.add_subparsers(dest="command", required=True)

    password = sub.add_parser("set-password", help="Menetapkan password seorang pengguna")
    password.add_argument("username")

    sub.add_parser("list-users", help="Menampilkan daftar pengguna dan status kredensialnya")
    lock = sub.add_parser("lock-user", help="Mengunci akun (tidak dapat masuk; baris tetap ada)")
    lock.add_argument("username")
    backtest = sub.add_parser(
        "backtest", help="Evaluasi mundur: prediksi H-1 dibandingkan kejadian nyata hari H"
    )
    backtest.add_argument("--dari", type=date.fromisoformat, required=True)
    backtest.add_argument("--sampai", type=date.fromisoformat, required=True)
    backtest.add_argument("--horizon", default="24H")
    backtest.add_argument(
        "--dry-run", action="store_true", help="Menghitung tanpa menulis satu baris pun"
    )

    arguments = parser.parse_args(argv)

    if arguments.command == "set-password":
        return set_password(arguments.username)
    if arguments.command == "lock-user":
        return lock_user(arguments.username)
    if arguments.command == "backtest":
        return run_backtest(arguments.dari, arguments.sampai, arguments.horizon, arguments.dry_run)
    return list_users()


if __name__ == "__main__":
    raise SystemExit(main())
