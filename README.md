# StreamFlix (Static Version — No Flask, No Server Logic)

Same Netflix-style movie recommender, rebuilt as a **static website**:
all the TF-IDF / cosine similarity computation happens once, offline, in
a Python script. The website itself is just HTML + CSS + JavaScript
reading a pre-built JSON file — nothing runs on a server while you
browse it.

## What changed from the Flask version

| Flask version | Static version |
|---|---|
| `app.py` computes recommendations live, per request | `scripts/build_recommendations.py` computes ALL recommendations once, ahead of time |
| Browser calls `/api/recommend?title=...` | Browser reads the already-computed list straight out of `data/movies.json` |
| Gradient placeholder cards only | Real poster images, fetched live from TMDB |
| Needs Flask running (`python app.py`) | Needs only a static file server (or none, with one small caveat below) |

## Project structure

```
movie-static/
├── data/
│   ├── tmdb_5000_movies.csv        # original dataset
│   └── movies.json                 # generated — all movies + precomputed recommendations
├── scripts/
│   ├── build_recommendations.py    # Step 1: TF-IDF + cosine similarity → movies.json
│   └── fetch_posters.py            # Step 2: adds real poster images from TMDB
├── index.html
├── style.css
├── script.js
├── requirements.txt
└── README.md
```

## Setup

### 1. Install Python dependencies (only needed to *build* the data, not to browse the site)

```bash
pip install -r requirements.txt
```

### 2. Build the recommendation data (required, run once)

```bash
python scripts/build_recommendations.py
```

This reads the CSV, computes TF-IDF + cosine similarity for all 4,800 movies,
and writes `data/movies.json`. Takes under a minute.

### 3. Add real poster images (optional but recommended)

1. Get a free TMDB API key: themoviedb.org → Settings → API → Create.
2. Create a file named `.env` in the project root:
   ```
   TMDB_API_KEY=your_key_here
   ```
3. Run:
   ```bash
   python scripts/fetch_posters.py
   ```
   This calls TMDB's API once per movie and saves each poster's path into
   `data/movies.json`. Takes a few minutes for ~4,800 movies. If you skip
   this step, cards just fall back to the gradient placeholder art.

### 4. Open the site

Browsers block `fetch()` of local JSON files opened directly (`file://`),
so serve the folder with any simple static server:

```bash
python3 -m http.server 8000
```

Then open **http://127.0.0.1:8000** in your browser.

(In VS Code, the **Live Server** extension does the same thing with one click —
right-click `index.html` → "Open with Live Server".)

## How the recommendation logic works

Unchanged from the Flask version — see the heavy comments in
`scripts/build_recommendations.py`:

1. Combine each movie's genres + keywords + tagline + overview into one text "soup."
2. Convert every soup into a TF-IDF vector (rare, distinctive words score higher).
3. Compute cosine similarity between every pair of movies.
4. For each movie, keep the top 12 most similar movies — precomputed and
   saved directly into `movies.json` as `{index, match}` pairs.

The only difference: this all happens **once**, in Python, ahead of time —
not per-click in a live server.

## About the poster images

Poster images are **hotlinked directly from TMDB's own image server**
(`https://image.tmdb.org`) — your browser fetches them straight from TMDB
when you view a card. This project does not download, store, or
redistribute any poster artwork itself; only the `poster_path` (a short
string like `/abc123.jpg`) is saved locally, which is just a filename,
not the image itself. Poster artwork remains the property of the
respective studios/distributors, per TMDB's terms of use.

## Extending it

- **Refresh data**: re-run `build_recommendations.py` any time the CSV changes.
- **More recommendations per movie**: change `top_n`/`[:12]` in `build_recommendations.py`.
- **Deploy for free**: since this is 100% static files, it can be hosted directly
  on GitHub Pages, Netlify, or Vercel with zero backend setup.
