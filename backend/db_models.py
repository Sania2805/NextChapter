from datetime import datetime
from enum import Enum

from sqlalchemy import Enum as SQLEnum, ForeignKey, String, UniqueConstraint, func, text
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class ReadingStatus(str, Enum):
    want_to_read = "want_to_read"
    reading = "reading"
    finished = "finished"


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(40))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))


class ReadingEntry(Base):
    __tablename__ = "reading_list"
    __table_args__ = (
        UniqueConstraint("user_id", "isbn", name="uq_reading_user_isbn"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    isbn: Mapped[str] = mapped_column(
        String(32).with_variant(String(32, collation="utf8mb4_bin"), "mysql")
    )
    reading_status: Mapped[ReadingStatus] = mapped_column(
        SQLEnum(ReadingStatus, name="reading_status", native_enum=False, create_constraint=True)
        .with_variant(mysql.ENUM(ReadingStatus), "mysql"),
        server_default="want_to_read",
    )
    created_at: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP"), onupdate=func.current_timestamp()
    )
