"""Titik masuk untuk Vercel Python runtime.

Vercel hanya menjalankan berkas di dalam folder api/, sedangkan kode aplikasi
tetap di paket app/. Folder induk ditambahkan ke sys.path supaya `import app`
berhasil tanpa memindahkan satu pun berkas.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402  (harus setelah sys.path disiapkan)

__all__ = ["app"]
