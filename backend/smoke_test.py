"""Create disposable accounts and verify the application against the configured database.

Use only a development or test database. No existing account is modified.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from database import COOKIE_SECURE, JWT_SECRET, ORIGINS, Session
from db_models import User
from main import app
from recommender import book_to_idx, work_key
from routes import COOKIE

origin = ORIGINS[0]
headers = {"Origin": origin, "X-NextChapter": "1"}
base_url = "https://testserver" if COOKIE_SECURE else "http://testserver"


def request(client, method, path, status, **kwargs):
    response = client.request(method, "/api" + path, **kwargs)
    assert response.status_code == status, (method, path, response.status_code, response.text)
    return response


def run():
    emails = []
    try:
        a, b, other_device = (TestClient(app, base_url=base_url) for _ in range(3))
        request(a, "GET", "/reading-list", 401)
        popular = request(a, "GET", "/books/popular", 200).json()
        isbn = popular[0]["isbn"]
        request(a, "GET", "/books/search", 200, params={"q": popular[0]["title"]})
        request(a, "GET", f"/books/{isbn}", 200)
        supported = next(iter(book_to_idx))
        assert request(a, "GET", f"/books/{supported}/recommendations", 200).json()["recommendations"]
        request(a, "GET", "/books/unsupported/recommendations", 404)
        first_draw = request(a, "GET", "/books/surprise", 200)
        first_pick = first_draw.json()["book"]
        assert first_draw.headers["cache-control"] == "no-store"
        assert first_pick["rating_count"] >= 5 and 1 <= first_pick["average_rating"] <= 10
        second_draw = request(a, "GET", "/books/surprise", 200).json()
        pick = second_draw["book"]
        assert work_key(first_pick["isbn"]) != work_key(pick["isbn"])
        assert all(work_key(book["isbn"]) != work_key(pick["isbn"]) for book in second_draw["previews"])
        assert request(a, "GET", f"/books/{pick['isbn']}", 200).json()["title"] == pick["title"]
        isbn = first_pick["isbn"]

        password = uuid4().hex
        for client in (a, b):
            body = {"username": "Smoke Reader", "email": f"smoke-{uuid4().hex}@example.com", "password": password}
            emails.append(body["email"])
            request(client, "POST", "/auth/register", 403, json=body)
            response = request(client, "POST", "/auth/register", 201, headers=headers, json=body)
            assert "httponly" in response.headers["set-cookie"].lower()
            assert "password_hash" not in response.json()
            request(client, "POST", "/auth/register", 409, headers=headers, json=body)
            request(client, "GET", "/auth/me", 200)
        with Session() as db:
            hashes = db.scalars(select(User.password_hash).where(User.email.in_(emails))).all()
            assert len(hashes) == 2 and all(x.startswith("$argon2id$") for x in hashes)

        request(a, "POST", "/reading-list", 403, headers={**headers, "Origin": "https://untrusted.invalid"}, json={"isbn": isbn})
        entry = request(a, "POST", "/reading-list", 201, headers=headers, json={"isbn": isbn}).json()
        next_pick = request(a, "GET", "/books/surprise", 200).json()["book"]
        assert work_key(next_pick["isbn"]) != work_key(isbn)
        assert work_key(next_pick["isbn"]) != work_key(pick["isbn"])
        entry_id = entry["id"]
        path = f"/reading-list/{entry_id}"
        request(a, "POST", "/reading-list", 409, headers=headers, json={"isbn": isbn})
        request(a, "POST", "/reading-list", 404, headers=headers, json={"isbn": "unknown"})
        assert request(b, "GET", "/reading-list", 200).json() == []
        request(b, "PATCH", path, 404, headers=headers, json={"reading_status": "finished"})
        request(b, "DELETE", path, 404, headers=headers)
        request(a, "PATCH", path, 422, headers=headers, json={"reading_status": "invalid"})
        changed = request(a, "PATCH", path, 200, headers=headers, json={"reading_status": "reading"}).json()
        assert changed["reading_status"] == "reading"
        request(a, "POST", "/auth/logout", 204, headers=headers)
        request(a, "GET", "/auth/me", 401)
        request(other_device, "POST", "/auth/login", 401, headers=headers, json={"email": emails[0], "password": "incorrect"})
        request(other_device, "POST", "/auth/login", 200, headers=headers, json={"email": emails[0], "password": password})
        assert request(other_device, "GET", "/reading-list", 200).json() == [changed]
        request(other_device, "DELETE", path, 204, headers=headers)
        assert request(other_device, "GET", "/reading-list", 200).json() == []
        now = datetime.now(timezone.utc)
        expired = jwt.encode({"sub": "1", "iat": now - timedelta(hours=3), "exp": now - timedelta(hours=1),
                              "iss": "nextchapter"}, JWT_SECRET, algorithm="HS256")
        other_device.cookies.clear()
        other_device.cookies.set(COOKIE, expired)
        assert "expired" in request(other_device, "GET", "/auth/me", 401).json()["detail"]
        print("Passed: catalog, KNN, validation, CSRF, cookies, expiry, persistence and account isolation.")
    finally:
        if emails:
            with Session.begin() as db:
                db.execute(delete(User).where(User.email.in_(emails)))


if __name__ == "__main__":
    run()

