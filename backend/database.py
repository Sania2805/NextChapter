import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", encoding="utf-8-sig")

ORIGINS = [origin.strip() for origin in os.getenv(
    "APP_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173"
).split(",") if origin.strip()]
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
JWT_SECRET = os.getenv("JWT_SECRET", "")

database_url = os.getenv("DATABASE_URL", "").strip()
if database_url:
    url = make_url(database_url).set(drivername="postgresql+psycopg")
    ca_file = os.getenv("DB_SSL_CA")
    if ca_file:
        url = url.update_query_dict({"sslmode": "verify-full", "sslrootcert": ca_file})
else:
    url = URL.create(
        "mysql+pymysql",
        username=os.getenv("DB_USER", "nextchapter"),
        password=os.getenv("DB_PASSWORD", ""),
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "nextchapter_db"),
        query={"charset": "utf8mb4"},
    )

engine = create_engine(url, pool_pre_ping=True, pool_recycle=1800, connect_args={"connect_timeout": 4})
Session = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    with Session() as db:
        yield db


