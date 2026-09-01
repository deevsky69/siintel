"""Hashing password dengan Argon2id (TASK 050, keputusan SDL-06).

Akun yang belum diberi kredensial menyimpan penanda `!` (konvensi berkas shadow):
akunnya ada, tetapi tidak dapat dipakai masuk. Verifikasi terhadap penanda itu
**selalu** gagal, dan tetap menjalankan perhitungan hash tiruan supaya lamanya
respons tidak membocorkan akun mana yang terkunci.
"""

from __future__ import annotations

from contextlib import suppress

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

#: Penanda akun terkunci — bukan kata sandi.
LOCKED_PASSWORD = "!"  # noqa: S105

_hasher = PasswordHasher()

#: Hash tiruan untuk menyamakan waktu verifikasi akun terkunci/tidak ada.
_DUMMY_HASH = _hasher.hash("prediksi-presisi-dummy")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def is_locked(password_hash: str) -> bool:
    return password_hash == LOCKED_PASSWORD


def verify_password(password: str, password_hash: str | None) -> bool:
    """Memeriksa password. Akun terkunci dan akun tak dikenal sama-sama gagal."""
    if password_hash is None or is_locked(password_hash):
        # Tetap jalankan verifikasi tiruan agar lamanya respons tidak membedakan
        # akun terkunci, akun tak dikenal, dan password salah.
        with suppress(VerifyMismatchError, InvalidHashError):
            _hasher.verify(_DUMMY_HASH, password)
        return False

    try:
        _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False
    return True


def needs_rehash(password_hash: str) -> bool:
    """Benar bila hash dibuat dengan parameter lama dan sebaiknya diperbarui."""
    if is_locked(password_hash):
        return False
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return False
