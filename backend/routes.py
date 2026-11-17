from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from database import COOKIE_SECURE, JWT_SECRET, ORIGINS, get_db
from db_models import ReadingEntry, User
from recommender import get_book_info, metadata_by_isbn
from schemas import Account, Login, ReadingItem, Register, SaveBook, StatusUpdate
from surprise import draw_surprise

router = APIRouter(prefix="/api")
Db = Annotated[Session, Depends(get_db)]
hasher = PasswordHasher()
dummy_hash = hasher.hash("unused-login-verification")
COOKIE = "__Host-nextchapter" if COOKIE_SECURE else "nextchapter_session"
SURPRISE_COOKIE = "nextchapter_last_surprise"


def require_origin(request: Request):
    if request.headers.get("origin") not in ORIGINS or request.headers.get("x-nextchapter") != "1":
        raise HTTPException(403, "Request origin is not allowed.")


def signing_key():
    if len(JWT_SECRET.encode()) < 32:
        raise HTTPException(503, "Authentication is not configured. Set JWT_SECRET on the server.")
    return JWT_SECRET


def start_session(response, user, key):
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": str(user.id), "iat": now, "exp": now + timedelta(hours=2), "iss": "nextchapter"},
        key, algorithm="HS256",
    )
    response.set_cookie(COOKIE, token, httponly=True, secure=COOKIE_SECURE, samesite="lax", path="/")


def current_user(request: Request, db: Db):
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "Sign in to continue.")
    key = signing_key()
    try:
        claims = jwt.decode(token, key, algorithms=["HS256"], issuer="nextchapter",
                            options={"require": ["sub", "iat", "exp", "iss"]})
        user_id = int(claims["sub"])
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(401, "Your session has expired or is invalid. Sign in again.")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(401, "Sign in again to continue.")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
csrf = [Depends(require_origin)]


def commit(db, conflict):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if exc.orig.args and exc.orig.args[0] == 1062:
            raise HTTPException(409, conflict) from exc
        raise


@router.post("/auth/register", response_model=Account, status_code=201, dependencies=csrf)
def register(body: Register, response: Response, db: Db):
    key = signing_key()
    user = User(username=body.username, email=body.email.lower(), password_hash=hasher.hash(body.password))
    db.add(user)
    commit(db, "An account with that email already exists.")
    start_session(response, user, key)
    return user


@router.post("/auth/login", response_model=Account, dependencies=csrf)
def login(body: Login, response: Response, db: Db):
    key = signing_key()
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    try:
        hasher.verify(user.password_hash if user else dummy_hash, body.password)
    except VerifyMismatchError:
        raise HTTPException(401, "Email or password is incorrect.")
    if user is None:
        raise HTTPException(401, "Email or password is incorrect.")
    if hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hasher.hash(body.password)
        db.commit()
    start_session(response, user, key)
    return user


@router.post("/auth/logout", status_code=204, dependencies=csrf)
def logout(response: Response):
    response.delete_cookie(COOKIE, httponly=True, secure=COOKIE_SECURE, samesite="lax", path="/")


@router.get("/auth/me", response_model=Account)
def me(user: CurrentUser):
    return user


@router.get("/books/surprise")
def surprise_book(
    request: Request, response: Response, db: Db,
    exclude_isbn: str | None = Query(default=None, max_length=64),
):
    saved = []
    if request.cookies.get(COOKIE):
        try:
            user = current_user(request, db)
            saved = db.scalars(select(ReadingEntry.isbn).where(ReadingEntry.user_id == user.id)).all()
        except HTTPException as exc:
            if exc.status_code not in (401, 503):
                raise
        except (OperationalError, ProgrammingError):
            # The public draw can still work while MySQL is unavailable.
            pass

    previous = filter(None, (exclude_isbn, request.cookies.get(SURPRISE_COOKIE)))
    try:
        result = draw_surprise(previous, saved)
    except FileNotFoundError as exc:
        raise HTTPException(503, "Surprise picks are temporarily unavailable.") from exc
    if result is None:
        raise HTTPException(503, "No new surprise picks are available right now.")

    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(SURPRISE_COOKIE, result["book"]["isbn"], httponly=True,
                        secure=COOKIE_SECURE, samesite="lax", path="/api/books/surprise")
    return result


def reading_item(row):
    return ReadingItem(
        id=row.id, isbn=row.isbn, reading_status=row.reading_status,
        created_at=row.created_at, updated_at=row.updated_at, book=get_book_info(row.isbn),
    )


def owned_entry(entry_id, user, db):
    row = db.scalar(select(ReadingEntry).where(
        ReadingEntry.id == entry_id, ReadingEntry.user_id == user.id
    ).with_for_update())
    if row is None:
        raise HTTPException(404, "Saved book not found.")
    return row


@router.get("/reading-list", response_model=list[ReadingItem])
def reading_list(user: CurrentUser, db: Db):
    rows = db.scalars(select(ReadingEntry).where(ReadingEntry.user_id == user.id)
                      .order_by(ReadingEntry.created_at.desc(), ReadingEntry.id.desc()))
    return [reading_item(row) for row in rows]


@router.post("/reading-list", response_model=ReadingItem, status_code=201, dependencies=csrf)
def save(body: SaveBook, user: CurrentUser, db: Db):
    if body.isbn not in metadata_by_isbn.index:
        raise HTTPException(404, "Book ISBN was not found in the catalog.")
    row = ReadingEntry(user_id=user.id, isbn=body.isbn, reading_status=body.reading_status)
    db.add(row)
    commit(db, "This edition is already in your reading list.")
    db.refresh(row)
    return reading_item(row)


@router.patch("/reading-list/{entry_id}", response_model=ReadingItem, dependencies=csrf)
def update(entry_id: int, body: StatusUpdate, user: CurrentUser, db: Db):
    row = owned_entry(entry_id, user, db)
    row.reading_status = body.reading_status
    db.flush()
    db.refresh(row)
    result = reading_item(row)
    db.commit()
    return result


@router.delete("/reading-list/{entry_id}", status_code=204, dependencies=csrf)
def remove(entry_id: int, user: CurrentUser, db: Db):
    db.delete(owned_entry(entry_id, user, db))
    db.commit()
