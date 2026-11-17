# NextChapter

NextChapter is a full-stack book discovery app built with React, Vite, and FastAPI. Start with a book you enjoyed, find similar titles from the Book-Crossing catalog, or let **Surprise Me!** pick your next read.

## Features

- **Book recommendations** use item-based collaborative filtering with cosine K-nearest neighbors. The API reranks candidates using shared reader ratings and groups editions of the same work.
- **Catalog search and popular books** let you browse by title, open ISBN-level details, and find popular picks when a title has too little rating data for similar-book recommendations.
- **Surprise Me!** spins through real catalog covers and reveals a book with its publication year and reader rating when available. The draw requires at least five explicit ratings and skips the previous pick.
- **Personal reading lists** let signed-in readers save editions and mark them as Want to read, Reading, or Finished.

## Local setup

Use Python 3.14 and Node.js 22.12 or later. Accounts and reading lists use MySQL 8 or PostgreSQL. Public discovery can run without a database.

### 1. Install Python dependencies

Run these commands from the repository root. The notebook requirements also install the API dependencies.

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r notebooks/requirements.txt
```

On macOS or Linux, use `python3.14 -m venv .venv` and substitute `.venv/bin/python` for `.\.venv\Scripts\python.exe` in the commands below. If you already have the local data and trained files, you can install only `backend/requirements.txt`.

### 2. Prepare the catalog and model

Download the CSV edition of the [Book Recommendation Dataset on Kaggle](https://www.kaggle.com/datasets/arashnic/book-recommendation-dataset). Extract `Books.csv`, `Ratings.csv`, and `Users.csv` into `data/raw/`. Preserve those filenames.

Open JupyterLab from the repository root and run each notebook in order with the project's Python kernel. Run the notebooks from `notebooks/` so their relative paths resolve.

```powershell
.\.venv\Scripts\python.exe -m jupyterlab
```

1. [Data cleaning](notebooks/01_data_cleaning.ipynb) writes the prepared CSVs to `data/processed/`.
2. [Exploratory analysis](notebooks/02_eda.ipynb) summarizes the dataset and saves book statistics.
3. [Model training](notebooks/03_model_training.ipynb) writes the catalog, popularity ranking, KNN model, sparse matrix, and ISBN mappings to `models/`. The evaluation cells can take several minutes.

The API loads `book_metadata.csv`, `popularity_ranking.csv`, `knn_model.pkl`, `book_user_matrix.pkl`, `train_books.pkl`, and `book_to_idx.pkl` from `models/`. Surprise Me also reads `books_clean.csv` and `explicit_ratings.csv` from `data/processed/`. The notebooks create both output directories. Load model files only from a source you trust.

### 3. Configure accounts and reading lists

For public discovery only, skip to step 4. For account features, start MySQL and run the following as a MySQL administrator on a new local setup. Replace the password placeholder with your own password.

```sql
CREATE DATABASE IF NOT EXISTS nextchapter_db CHARACTER SET utf8mb4;
CREATE USER 'nextchapter'@'127.0.0.1' IDENTIFIED BY 'REPLACE_WITH_YOUR_PASSWORD';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
  ON nextchapter_db.* TO 'nextchapter'@'127.0.0.1';
```

Copy [the backend environment template](backend/.env.example) to `backend/.env`. Set `DB_PASSWORD` to the MySQL password and set `JWT_SECRET` to a separate random value. The following command generates one. Then run the migration against the configured database.

```powershell
Copy-Item backend/.env.example backend/.env
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
# Edit backend/.env before running the migration.
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
```

### 4. Run the API and frontend

From the repository root, start FastAPI.

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In a second terminal, start Vite. On macOS or Linux, use `npm` in place of `npm.cmd`.

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open [NextChapter](http://127.0.0.1:5173) or the [FastAPI docs](http://127.0.0.1:8000/docs). Vite forwards `/api` to FastAPI. Leave `VITE_API_BASE_URL` blank for local development. [The frontend template](frontend/.env.example) documents the optional override.

## Repository layout

| Path | Contents |
| --- | --- |
| `frontend/` | React app, Vite configuration, and npm lockfile |
| `backend/` | FastAPI routes, recommender, database models, and Alembic migrations |
| `notebooks/` | Data cleaning, analysis, and model training |
| `data/`, `models/` | Local dataset and generated files created during setup |

## Checks

- From `frontend/`, run `npm run build` to build the production frontend.
- From the repository root, run `.\.venv\Scripts\python.exe backend/smoke_test.py` against a migrated **development** database. The script creates and cleans up disposable test accounts.
- To check discovery without a database, open `/api/books/popular` and `/api/books/surprise` in the API docs, then try title search and Surprise Me in the app.

## Publishing to GitHub

The repository tracks source code, dependency manifests, environment templates, and the three pipeline notebooks. [The ignore rules](.gitignore) keep local `.env` files, datasets, generated models, dependency folders, builds, and backup archives out of Git.

If this is the first push, create an empty GitHub repository. From the project root, initialize Git and inspect the dry run before staging. Replace the example remote URL with your repository URL.

```powershell
git init -b main
git add --dry-run .
git add .
git diff --cached --stat
git commit -m "Initial commit for NextChapter"
git remote add origin https://github.com/YOUR-USERNAME/NextChapter.git
git push -u origin main
```

For a deployment, build the frontend with `npm run build`, serve its output over HTTPS, and route `/api` on the same origin to FastAPI. Configure the server to return `index.html` for client-side routes. Provision the generated runtime files separately. Set `COOKIE_SECURE=true`, the exact public origin in `APP_ORIGINS`, and a deployment-specific `JWT_SECRET` on the API server.

To use hosted PostgreSQL, set `DATABASE_URL` on the API server to the provider's PostgreSQL connection URI. NextChapter uses this URI in place of the local MySQL settings. For [Aiven PostgreSQL](https://aiven.io/docs/products/postgresql/get-started), upload the [Aiven CA certificate](https://aiven.io/docs/platform/concepts/tls-ssl-certificates) as a server file and set `DB_SSL_CA` to its path to verify the server's identity. Run `python -m alembic -c backend/alembic.ini upgrade head` against the new database before serving requests. A fresh database starts with empty accounts and reading lists.

For the NextChapter Render service, use the Python runtime and leave **Root Directory** blank. Set **Build Command** to `bash backend/render-build.sh` and **Start Command** to `bash backend/render-start.sh`. The build script downloads `nextchapter-runtime.zip` from the private `Sania2805/NextChapter-runtime` release tagged `v1` using `RUNTIME_TOKEN`. The start script runs the Alembic migration and starts FastAPI on Render's assigned port.

## Dataset credit

The Book-Crossing dataset was collected by Cai-Nicolas Ziegler from the Book-Crossing community. Dataset reference is Cai-Nicolas Ziegler, Sean M. McNee, Joseph A. Konstan, and Georg Lausen, *Improving Recommendation Lists Through Topic Diversification*, WWW 2005. [GroupLens dataset page](https://grouplens.org/datasets/book-crossing/) · [University of Freiburg project and publication](https://dbis.informatik.uni-freiburg.de/forschung/projekte/2nd-Gen-RS/index.html)
