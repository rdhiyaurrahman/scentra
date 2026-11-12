"""Autentikasi dan hak akses (FR-01, NFR 9.1).

Hash password memakai PBKDF2-HMAC-SHA256 dari pustaka standar Python, jadi tidak
perlu paket native yang sering gagal dipasang di Windows. Password tidak pernah
disimpan dalam bentuk teks biasa.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from .db import get_session
from .models import User

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-ganti-saat-deployment")
ALGORITHM = "HS256"
TOKEN_TTL_HOURS = 12
_ITERATIONS = 240_000

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, expected = stored.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), int(iterations)
        )
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(digest.hex(), expected)


def create_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def current_user(
    token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sesi tidak valid atau sudah berakhir.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise unauthorized
    user = session.get(User, int(payload.get("sub", 0)))
    if user is None or not user.is_active:
        raise unauthorized
    return user


def require_roles(*roles: str):
    """Batasi endpoint ke peran tertentu (matriks hak akses PRD bab 4.3)."""

    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tindakan ini hanya untuk peran: {', '.join(roles)}.",
            )
        return user

    return dependency


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.exec(select(User).where(User.email == email)).first()
