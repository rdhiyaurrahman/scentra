import os

from sqlmodel import Session, SQLModel, create_engine

# PostgreSQL untuk menjalankan prototipe (lihat docker-compose.yml).
# SQLite dipakai otomatis oleh pytest supaya pengujian tidak butuh server.
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://scentra:scentra@localhost:5432/scentra"
)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
