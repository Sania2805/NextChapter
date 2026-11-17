from collections import defaultdict
from heapq import nsmallest
from html import unescape
from pathlib import Path
from sys import intern
from typing import NamedTuple

import joblib
import numpy as np
import pandas as pd

from works import AUTHOR_CORRECTIONS, identify_work, normalize

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
knn_model = joblib.load(MODEL_DIR / "knn_model.pkl")
book_user_matrix = joblib.load(MODEL_DIR / "book_user_matrix.pkl").tocsr()
train_books = tuple(map(str, joblib.load(MODEL_DIR / "train_books.pkl")))
book_to_idx = joblib.load(MODEL_DIR / "book_to_idx.pkl")

popular_isbns = tuple(pd.read_csv(
    MODEL_DIR / "popularity_ranking.csv", usecols=["isbn"], dtype={"isbn": str}
)["isbn"].dropna())
rating_presence = book_user_matrix.copy()
rating_presence.eliminate_zeros()
rating_presence.data = np.ones(rating_presence.nnz, dtype=np.int32)
rating_counts = rating_presence.getnnz(axis=1)

class CatalogBook(NamedTuple):
    title: str
    author: str
    image: str
    work: tuple[str, str]
    search_title: str


def load_catalog():
    catalog = {}
    editions_by_work = defaultdict(list)
    # Keep only the fields used by the API, and release raw CSV rows between chunks.
    with pd.read_csv(MODEL_DIR / "book_metadata.csv", dtype={"isbn": str}, chunksize=8192) as chunks:
        for chunk in chunks:
            for row in chunk.fillna("").itertuples(index=False):
                isbn = row.isbn
                if isbn in catalog:
                    continue
                author_key, canonical_title = identify_work(isbn, row.title, row.author)
                search_title = normalize(row.title)
                key = (intern(author_key), canonical_title)
                catalog[isbn] = CatalogBook(
                    unescape(row.title),
                    unescape(AUTHOR_CORRECTIONS.get(isbn, row.author)),
                    row.image_l or row.image_m,
                    key,
                    canonical_title if search_title == canonical_title else search_title,
                )
                if isbn in book_to_idx:
                    editions_by_work[key].append(isbn)

    for editions in editions_by_work.values():
        editions.sort(key=lambda isbn: (-rating_counts[book_to_idx[isbn]], isbn))
    return catalog, editions_by_work


catalog, model_editions = load_catalog()


def book_exists(isbn):
    return isbn in catalog


def work_key(isbn):
    book = catalog.get(isbn)
    return book.work if book else ("isbn", isbn)


def has_model_editions(isbn):
    return isbn in book_to_idx or work_key(isbn) in model_editions


def get_book_info(isbn):
    isbn = str(isbn)
    book = catalog.get(isbn)
    if book is None:
        return {"isbn": isbn, "title": "Unknown", "author": "", "image": ""}

    return {
        "isbn": isbn,
        "title": book.title,
        "author": book.author,
        "image": book.image,
    }


def search_books(query, limit=10, *, prefer_model=False):
    query_key = normalize(query)
    if not query_key:
        return []

    matches = {}
    for isbn, book in catalog.items():
        title = book.search_title
        key = book.work
        canonical_title = key[1] if key[0] != "isbn" else title
        if query_key not in title and query_key not in canonical_title:
            continue
        exact = query_key in (title, canonical_title)
        if key not in matches or exact and not matches[key][1]:
            matches[key] = (isbn, exact)

    def ranked_matches():
        for key, (matched_isbn, exact) in matches.items():
            editions = model_editions.get(key)
            representative = editions[0] if editions else matched_isbn
            count = rating_counts[book_to_idx[representative]] if editions else 0
            priority = (not editions, not exact) if prefer_model else (not exact, not editions)
            yield (*priority, -count), representative

    return [
        {**get_book_info(isbn), "available": has_model_editions(isbn)}
        for _, isbn in nsmallest(limit, ranked_matches())
    ]


MAX_SOURCE_EDITIONS = 4
MIN_SHARED_READERS = 2
OVERLAP_SHRINKAGE = 3
SOURCE_SHRINKAGE = 10


def recommend_books(isbn, limit=10):
    isbn = str(isbn)
    source_work = work_key(isbn)
    editions = model_editions.get(source_work, ())
    sources = list(editions[:MAX_SOURCE_EDITIONS])
    if isbn in book_to_idx and isbn not in sources:
        sources = [isbn, *sources[:MAX_SOURCE_EDITIONS - 1]]
    if not sources:
        return []

    rows = [book_to_idx[edition] for edition in sources]
    # Retrieve enough candidates to fill the requested limit after filtering
    # and reranking. At this model size a single full batch is inexpensive.
    distances, indices = knn_model.kneighbors(
        book_user_matrix[rows], n_neighbors=len(train_books)
    )
    shared_readers = (rating_presence[rows] @ rating_presence.T).toarray()
    best = {}
    source_support = rating_counts[rows] / (rating_counts[rows] + SOURCE_SHRINKAGE)
    for offset, (distances_row, indices_row) in enumerate(zip(distances, indices)):
        for distance, index in zip(distances_row, indices_row):
            similarity = float(1 - distance)
            if similarity <= 0:
                break
            overlap = int(shared_readers[offset, index])
            if overlap < MIN_SHARED_READERS:
                continue
            candidate = train_books[index]
            book = catalog.get(candidate)
            if book is None:
                continue
            key = book.work
            if key == source_work:
                continue

            # Use the best supported ISBN pair. Summing across editions could
            # count the same reader multiple times.
            adjusted = similarity * overlap / (overlap + OVERLAP_SHRINKAGE) * source_support[offset]
            evidence = (adjusted, overlap, similarity, candidate)
            if key not in best or evidence > best[key]:
                best[key] = evidence

    return [
        {**get_book_info(candidate), "similarity": round(similarity, 4)}
        for _, _, similarity, candidate in sorted(best.values(), reverse=True)[:limit]
    ]


def get_popular_books(limit=10, exclude_isbn=None):
    results = []
    seen = {work_key(exclude_isbn)} if exclude_isbn else set()
    for isbn in popular_isbns:
        book = catalog.get(isbn)
        if book is None:
            continue
        key = book.work
        if key in seen:
            continue
        seen.add(key)
        results.append(get_book_info(isbn))
        if len(results) >= limit:
            break
    return results
