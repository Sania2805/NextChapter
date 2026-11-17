
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, ProgrammingError

from database import ORIGINS
from routes import router

from recommender import (
    has_model_editions,
    book_exists,
    get_book_info,
    search_books,
    recommend_books,
    get_popular_books,
)

app = FastAPI(
    title="Book Recommendation API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-NextChapter"]
)


@app.get("/")
def home():
    return {
        "message": "Book Recommendation API is running!"
    }


@app.get("/api/books/search")
def search(
    q: str = Query(min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    prefer_model: bool = False,
):
    return search_books(q, limit, prefer_model=prefer_model)


@app.get("/api/books/popular")
def popular(
    limit: int = Query(default=10, ge=1, le=50),
    exclude_isbn: str | None = None
):
    return get_popular_books(limit, exclude_isbn)


@app.get("/api/books/{isbn}/recommendations")
def recommendations(
    isbn: str,
    limit: int = Query(default=10, ge=1, le=50)
):
    results = recommend_books(isbn, limit)

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No recommendations with enough shared reader ratings"
        )

    return {
        "book": get_book_info(isbn),
        "recommendations": results
    }


@app.middleware("http")
async def private_responses(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith(("/api/auth/", "/api/reading-list")):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    errors = exc.errors()
    return JSONResponse(status_code=422, content={
        "detail": "; ".join(f"{error['loc'][-1]}: {error['msg']}" for error in errors)
    })


@app.exception_handler(OperationalError)
@app.exception_handler(ProgrammingError)
async def database_unavailable(request, exc):
    return JSONResponse(status_code=503, content={
        "detail": "The database is unavailable or not initialized. Check the connection and run the migrations."
    })


# Register the static surprise route before the ISBN route.
app.include_router(router)


@app.get("/api/books/{isbn}")
def book_details(isbn: str):
    if not book_exists(isbn):
        raise HTTPException(404, "Book not found in the catalog.")
    return {**get_book_info(isbn), "available": has_model_editions(isbn)}



