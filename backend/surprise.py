from functools import lru_cache
from pathlib import Path
from random import choice, sample

import pandas as pd

from recommender import get_book_info, metadata_by_isbn, work_key

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
# About 14,000 editions in Book-Crossing have at least five explicit ratings.
MIN_EXPLICIT_RATINGS = 5
PREVIEW_COUNT = 8


@lru_cache(maxsize=1)
def surprise_pool():
    ratings = pd.read_csv(
        DATA_DIR / "explicit_ratings.csv", usecols=["isbn", "rating"], dtype={"isbn": str}
    )
    stats = (
        ratings[ratings["rating"].between(1, 10)]
        .groupby("isbn")["rating"].agg(["count", "mean"])
    )
    eligible = stats[stats["count"] >= MIN_EXPLICIT_RATINGS].sort_values("count", ascending=False)
    years = pd.read_csv(
        DATA_DIR / "books_clean.csv", usecols=["isbn", "year"], dtype={"isbn": str}
    ).drop_duplicates("isbn").set_index("isbn")["year"]

    books = {}
    for isbn, stat in eligible.iterrows():
        if isbn not in metadata_by_isbn.index:
            continue
        key = work_key(isbn)
        if key in books:
            continue
        book = get_book_info(isbn)
        if not book["title"].strip():
            continue
        year = years.get(isbn)
        books[key] = {
            **book,
            "year": int(year) if pd.notna(year) and year > 0 else None,
            "average_rating": round(float(stat["mean"]), 1),
            "rating_count": int(stat["count"]),
        }
    return books


def draw_surprise(previous_isbns, saved_isbns):
    pool = surprise_pool()
    previous = {work_key(isbn) for isbn in previous_isbns}
    saved = {work_key(isbn) for isbn in saved_isbns}
    fresh = [key for key in pool if key not in previous]
    if not fresh:
        return None

    eligible = [key for key in fresh if key not in saved] or fresh
    winner = choice(eligible)
    preview_keys = [key for key in pool if key != winner]
    previews = sample(preview_keys, min(PREVIEW_COUNT, len(preview_keys)))
    return {"book": pool[winner], "previews": [pool[key] for key in previews]}
