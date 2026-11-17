from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints

from db_models import ReadingStatus


class Login(BaseModel):
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=1, max_length=128)]


class Register(Login):
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=40)]
    password: Annotated[str, StringConstraints(min_length=12, max_length=128)]


class Account(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: EmailStr
    created_at: datetime


class StatusUpdate(BaseModel):
    reading_status: ReadingStatus


class SaveBook(StatusUpdate):
    isbn: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
    reading_status: ReadingStatus = ReadingStatus.want_to_read


class Book(BaseModel):
    isbn: str
    title: str
    author: str
    image: str


class ReadingItem(StatusUpdate):
    id: int
    isbn: str
    created_at: datetime
    updated_at: datetime
    book: Book
