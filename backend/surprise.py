import json
from functools import lru_cache
from pathlib import Path
from random import choice, sample

import pandas as pd

from recommender import book_exists, get_book_info, work_key

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
POOL_PATH = DATA_DIR / "surprise_pool.json"
# About 14,000 editions in Book-Crossing have at least five explicit ratings.
MIN_EXPLICIT_RATINGS = 5
PREVIEW_COUNT = 8


def build_surprise_pool():
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
    for isbn, count, average in eligible.itertuples():
        if not book_exists(isbn):
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
            "average_rating": round(float(average), 1),
            "rating_count": int(count),
        }
    return books


@lru_cache(maxsize=1)
def surprise_pool():
    if not POOL_PATH.is_file():
        return build_surprise_pool()

    with POOL_PATH.open(encoding="utf-8") as source:
        books = json.load(source)
    return {work_key(book["isbn"]): book for book in books}


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


if __name__ == "__main__":
    pool = build_surprise_pool()
    with POOL_PATH.open("w", encoding="utf-8") as target:
        json.dump(list(pool.values()), target, ensure_ascii=False, separators=(",", ":"))
    print(f"Prepared {len(pool):,} eligible Surprise Me picks.")
