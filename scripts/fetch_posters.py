"""
scripts/fetch_posters.py
==========================
Run this AFTER build_recommendations.py, and AFTER you have a free TMDB
API key (see README.md for how to get one).

For every movie in data/movies.json, this calls TMDB's API to get its
real poster_path, then writes that back into the same file. The website
then builds the actual image URL from that path (see script.js).

This only needs to be run ONCE -- after this, movies.json has everything
the static site needs, and you never need Python or your API key again
to just browse the site.

SPEED: requests run CONCURRENTLY (default 20 at a time) instead of one
at a time. Fetching ~4,800 movies takes roughly 1-3 minutes this way,
versus 15-20+ minutes doing them sequentially. TMDB's free tier easily
handles this -- their documented limit is far higher than 20 requests
in flight. If you ever see repeated failures, lower MAX_WORKERS below.

The script is also resumable: if you stop it partway through (or it
fails partway), rerunning it only fetches posters for movies that don't
already have one -- it won't redo work.

Setup:
    1. Create a file named .env in the project root with one line:
       TMDB_API_KEY=your_key_here
    2. pip install requests python-dotenv

Run:
    python scripts/fetch_posters.py
"""

import json
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("TMDB_API_KEY")
DATA_PATH = "data/movies.json"
TMDB_MOVIE_URL = "https://api.themoviedb.org/3/movie/{id}"

# How many requests to have in flight at once. 20 is a safe, fast default
# for TMDB's free tier. Raise it (e.g. 40) if it's running smoothly and
# you want it even faster; lower it (e.g. 8) if you start seeing a lot
# of failures/timeouts.
MAX_WORKERS = 20

# A single requests.Session reuses HTTP connections instead of opening a
# new one per request, which meaningfully speeds up thousands of calls.
session = requests.Session()


def fetch_poster_path(movie_id: int) -> str | None:
    """Returns the poster_path string (e.g. '/abc123.jpg') or None if
    the movie has no poster or the request fails.
    """
    try:
        response = session.get(
            TMDB_MOVIE_URL.format(id=movie_id),
            params={"api_key": API_KEY},
            timeout=10,
        )
        if response.status_code != 200:
            return None
        return response.json().get("poster_path")
    except requests.RequestException:
        return None


def main():
    if not API_KEY:
        print("ERROR: TMDB_API_KEY not found.")
        print("Create a .env file in the project root with:")
        print("  TMDB_API_KEY=your_key_here")
        return

    with open(DATA_PATH) as f:
        movies = json.load(f)

    # Resumability: skip any movie that already has a poster_path from
    # a previous run (None means "not fetched yet"; "" would mean
    # "fetched, TMDB has no poster" -- we don't currently write that,
    # but the check is here in case you ever add it).
    pending = [m for m in movies if m.get("poster_path") is None]
    already_done = len(movies) - len(pending)
    if already_done:
        print(f"{already_done} movies already have a poster from a previous run -- skipping those.")

    if not pending:
        print("Nothing to fetch -- every movie already has a poster (or a confirmed miss).")
        return

    print(f"Fetching posters for {len(pending)} movies with {MAX_WORKERS} concurrent requests...")

    found, missing, done_count = 0, 0, 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        future_to_movie = {pool.submit(fetch_poster_path, m["id"]): m for m in pending}

        for future in as_completed(future_to_movie):
            movie = future_to_movie[future]
            poster_path = future.result()
            movie["poster_path"] = poster_path

            if poster_path:
                found += 1
            else:
                missing += 1
            done_count += 1

            if done_count % 200 == 0 or done_count == len(pending):
                print(f"  {done_count}/{len(pending)} processed  (found: {found}, missing: {missing})")

    with open(DATA_PATH, "w") as f:
        json.dump(movies, f, allow_nan=False)

    print(f"\nDone. {found} posters found, {missing} movies will use the gradient fallback card.")
    print(f"Updated {DATA_PATH} -- the website is now ready to use.")


if __name__ == "__main__":
    main()