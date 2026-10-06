"""
scripts/build_recommendations.py
=================================
Run this ONCE (offline) to do all the heavy lifting: load the dataset,
compute TF-IDF vectors, compute cosine similarity, and pre-calculate the
top recommendations for every single movie.

Everything gets written to data/movies.json -- a plain static file the
website reads with fetch(). No server, no Flask, no live computation
in the browser. This is exactly what "static site" means: all the work
happens ahead of time, and the site just displays the result.

Run:
    python scripts/build_recommendations.py

Output:
    data/movies.json
"""

import ast
import json
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_PATH = "data/tmdb_5000_movies.csv"
OUTPUT_PATH = "data/movies.json"

# Same placeholder gradient colors as before -- used as a fallback for
# any movie whose real poster can't be found (e.g. fetch_posters.py
# wasn't run yet, or TMDB has no poster for that title).
GENRE_COLORS = {
    "Action": ("#e50914", "#7a0d13"), "Adventure": ("#ff9800", "#8a4400"),
    "Animation": ("#00bcd4", "#0d5d68"), "Comedy": ("#ffd54f", "#8a6d00"),
    "Crime": ("#616161", "#1a1a1a"), "Documentary": ("#4caf50", "#1b5e20"),
    "Drama": ("#9c27b0", "#4a0e57"), "Family": ("#03a9f4", "#01516e"),
    "Fantasy": ("#7c4dff", "#2f1a80"), "History": ("#8d6e63", "#3e2723"),
    "Horror": ("#212121", "#000000"), "Music": ("#ec407a", "#7a0e35"),
    "Mystery": ("#37474f", "#0f171a"), "Romance": ("#ff4081", "#8a0037"),
    "Science Fiction": ("#00e5ff", "#00636f"), "Thriller": ("#d32f2f", "#4a0000"),
    "War": ("#5d4037", "#231108"), "Western": ("#a1887f", "#4e342e"),
    "TV Movie": ("#607d8b", "#263238"),
}
DEFAULT_COLORS = ("#333333", "#0a0a0a")


def parse_json_list(text, key="name", top_n=None):
    if pd.isna(text):
        return []
    try:
        items = ast.literal_eval(text)
        names = [item[key] for item in items]
        return names[:top_n] if top_n else names
    except (ValueError, SyntaxError):
        return []


def main():
    print("Loading dataset...")
    df = pd.read_csv(DATA_PATH)

    df["overview"] = df["overview"].fillna("")
    df["tagline"] = df["tagline"].fillna("")
    df["genres_list"] = df["genres"].apply(lambda x: parse_json_list(x, "name"))
    df["keywords_list"] = df["keywords"].apply(lambda x: parse_json_list(x, "name", top_n=10))
    df["primary_genre"] = df["genres_list"].apply(lambda g: g[0] if g else "Drama")
    df["title_lower"] = df["title"].astype(str).str.lower().str.strip()

    df.sort_values("popularity", ascending=False, inplace=True)
    df.drop_duplicates(subset="title_lower", keep="first", inplace=True)
    df.reset_index(drop=True, inplace=True)
    print(f"{len(df)} unique movies after cleaning.")

    print("Building text soup...")
    genres_text = df["genres_list"].apply(lambda g: " ".join(w.replace(" ", "") for w in g))
    keywords_text = df["keywords_list"].apply(lambda k: " ".join(w.replace(" ", "") for w in k))
    df["soup"] = (genres_text + " ") * 3 + (keywords_text + " ") * 2 + df["tagline"] + " " + df["overview"]

    print("Computing TF-IDF + cosine similarity (this is the slow step)...")
    vectorizer = TfidfVectorizer(stop_words="english", min_df=2)
    tfidf_matrix = vectorizer.fit_transform(df["soup"])
    similarity_matrix = cosine_similarity(tfidf_matrix, tfidf_matrix)

    print("Pre-computing top 12 recommendations for every movie...")
    movies = []
    for idx, row in df.iterrows():
        scores = list(enumerate(similarity_matrix[idx]))
        scores = sorted(scores, key=lambda x: x[1], reverse=True)
        scores = [s for s in scores if s[0] != idx][:12]

        color_start, color_end = GENRE_COLORS.get(row["primary_genre"], DEFAULT_COLORS)

        # A few movies have no release_date (NaN). Python's json module
        # writes NaN as a literal, which is NOT valid JSON and breaks
        # JSON.parse() in the browser -- so we convert it to None here,
        # which becomes proper JSON `null`.
        release_date = row.get("release_date", "")
        if pd.isna(release_date):
            release_date = None

        movies.append({
            "id": int(row["id"]),                 # TMDB movie id -- used later to fetch the real poster
            "title": row["title"],
            "overview": row["overview"][:220] + ("..." if len(row["overview"]) > 220 else ""),
            "genres": row["genres_list"][:3],
            "rating": round(float(row["vote_average"]), 1),
            "vote_count": int(row["vote_count"]),
            "popularity": float(row["popularity"]),
            "release_date": release_date,
            "color_start": color_start,
            "color_end": color_end,
            "poster_path": None,   # filled in later by fetch_posters.py
            "recommendations": [
                {"index": int(i), "match": round(float(score) * 100)}
                for i, score in scores
            ],
        })

    with open(OUTPUT_PATH, "w") as f:
        json.dump(movies, f, allow_nan=False)

    print(f"Wrote {len(movies)} movies to {OUTPUT_PATH}")
    print("Next: run scripts/fetch_posters.py to add real poster images (needs a TMDB API key).")


if __name__ == "__main__":
    main()
