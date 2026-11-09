import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .routes import router

app = FastAPI(
    title="Scentra Manual Unified Inbox API",
    version="1.0.0",
    description=(
        "API internal untuk pencatatan manual percakapan pelanggan dari Shopee, "
        "TikTok Shop, dan Lazada. Tidak ada koneksi ke API marketplace mana pun."
    ),
)

# localhost dan 127.0.0.1 adalah origin berbeda bagi browser, jadi keduanya diizinkan
# supaya prototipe tetap jalan apa pun alamat yang dibuka penguji.
origins = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "marketplace_api_connected": False}
