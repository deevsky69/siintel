"""Perintah administrasi (TASK 050).

`set-password` menetapkan kredensial akun **di server**, bukan lewat kode. Password
tidak pernah masuk repository, tidak pernah ditulis ke berkas seed, dan tidak muncul
sebagai argumen perintah — dimasukkan lewat prompt tersembunyi.

Contoh:

    pnpm user:password -- demo.pimpinan
"""

from __future__ import annotations

import argparse
import getpass
import sys

from sqlalchemy import select

from .db import get_session_factory
from .models import User
from .security.passwords import hash_password

MINIMUM_LENGTH = 12


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="predpol", description="Administrasi PREDIKSI PRESISI")
    sub = parser.add_subparsers(dest="command", required=True)

    password = sub.add_parser("set-password", help="Menetapkan password seorang pengguna")
    password.add_argument("username")

    sub.add_parser("list-users", help="Menampilkan daftar pengguna dan status kredensialnya")

    arguments = parser.parse_args(argv)

    if arguments.command == "set-password":
        return set_password(arguments.username)
    return list_users()


if __name__ == "__main__":
    raise SystemExit(main())
