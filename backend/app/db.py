import os

from sqlmodel import Session, SQLModel, create_engine

# PostgreSQL untuk menjalankan prototipe (lihat docker-compose.yml).
# SQLite dipakai otomatis oleh pytest supaya pengujian tidak butuh server.
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://scentra:scentra@localhost:5432/scentra"
)

def normalize_db_url(url: str) -> str:
    """Penyedia Postgres (Neon, Supabase, Vercel) memberi URL berawalan
    "postgres://" atau "postgresql://" tanpa nama driver, sedangkan SQLAlchemy
    membutuhkannya. URL SQLite dan yang sudah lengkap dibiarkan apa adanya."""
    for prefix in ("postgresql+psycopg://", "postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


DATABASE_URL = normalize_db_url(DATABASE_URL)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
# pool_pre_ping: di serverless koneksi lama sering sudah ditutup penyedia database
# sebelum fungsi dipanggil lagi, jadi setiap koneksi diuji dulu sebelum dipakai.
engine = create_engine(
    DATABASE_URL, echo=False, connect_args=connect_args, pool_pre_ping=True
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
