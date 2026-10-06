/*
  script.js  (static version -- no Flask, no backend)
  ======================================================
  Everything the Flask version did with API endpoints, this version does
  by loading ONE static file (data/movies.json) once, then doing all
  lookups, searching, and sorting directly in the browser with plain
  JavaScript array methods.

  Real poster images are hotlinked straight from TMDB's own image
  server at https://image.tmdb.org -- the browser fetches them live
  from TMDB, this site never stores or re-hosts the images themselves.
*/

const TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500";

let MOVIES = [];               // the full dataset, loaded once
const cardTemplate = document.getElementById("cardTemplate");

// ---------------------------------------------------------------------
// Load the pre-computed data. This replaces every /api/... call the
// Flask version made -- it all already happened offline in Python.
// ---------------------------------------------------------------------
async function loadMovies() {
  const res = await fetch("data/movies.json");
  MOVIES = await res.json();
}

// ---------------------------------------------------------------------
// Card builder -- same idea as before, but now checks for a real
// poster_path first and falls back to the generated gradient card
// only if TMDB has no poster for that movie.
// ---------------------------------------------------------------------
function buildCard(movie, matchPercent = null) {
  const node = cardTemplate.content.cloneNode(true);

  const art = node.querySelector(".card-art");
  if (movie.poster_path) {
    art.style.backgroundImage = `url(${TMDB_IMAGE_BASE}${movie.poster_path})`;
    art.classList.add("has-poster");
  } else {
    art.style.background = `linear-gradient(160deg, ${movie.color_start}, ${movie.color_end})`;
  }

  node.querySelector(".card-watermark").textContent = movie.title.charAt(0).toUpperCase();
  node.querySelector(".card-title").textContent = movie.title;
  node.querySelector(".card-rating span").textContent = movie.rating.toFixed(1);
  node.querySelector(".card-overview").textContent = movie.overview || "No synopsis available.";

  const genresWrap = node.querySelector(".card-genres");
  (movie.genres || []).forEach((g) => {
    const span = document.createElement("span");
    span.textContent = g;
    genresWrap.appendChild(span);
  });

  if (matchPercent !== null) {
    const badge = node.querySelector(".match-badge");
    badge.textContent = `${matchPercent}% match`;
    badge.classList.remove("hidden");
  }

  const card = node.querySelector(".card");
  const goToRecommendations = () => showRecommendations(movie);
  card.addEventListener("click", goToRecommendations);
  node.querySelector(".btn-similar").addEventListener("click", (e) => {
    e.stopPropagation();
    goToRecommendations();
  });

  return node;
}

function renderRow(container, movies, matchLookup = null) {
  container.innerHTML = "";
  movies.forEach((movie) => {
    const match = matchLookup ? matchLookup.get(movie) : null;
    container.appendChild(buildCard(movie, match));
  });
}

// ---------------------------------------------------------------------
// HERO: the single most popular movie
// ---------------------------------------------------------------------
function renderHero() {
  const top = [...MOVIES].sort((a, b) => b.popularity - a.popularity)[0];
  if (!top) return;

  document.getElementById("heroTitle").textContent = top.title;
  document.getElementById("heroOverview").textContent = top.overview;
  document.getElementById("heroRating").textContent = `\u2605 ${top.rating.toFixed(1)}`;
  document.getElementById("heroGenres").textContent = (top.genres || []).join("  \u2022  ");
  document.getElementById("heroRecommendBtn").onclick = () => showRecommendations(top);
}

// ---------------------------------------------------------------------
// GENRE ROWS: computed client-side from the already-loaded data
// (this used to be two separate API calls -- /api/genres then
// /api/genre/<name> -- now it's just array filtering, instantly).
// ---------------------------------------------------------------------
function topGenres(n = 6) {
  const counts = new Map();
  MOVIES.forEach((m) => (m.genres || []).forEach((g) => counts.set(g, (counts.get(g) || 0) + 1)));
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, n).map(([g]) => g);
}

function moviesInGenre(genre, limit = 20) {
  return MOVIES
    .filter((m) => (m.genres || []).includes(genre))
    .sort((a, b) => b.popularity - a.popularity)
    .slice(0, limit);
}

function renderGenreRows() {
  const main = document.getElementById("genreRows");
  main.innerHTML = "";

  topGenres(6).forEach((genre) => {
    const section = document.createElement("section");
    section.className = "row-section";

    const title = document.createElement("h2");
    title.className = "row-title";
    title.textContent = genre;
    section.appendChild(title);

    const row = document.createElement("div");
    row.className = "card-row";
    section.appendChild(row);

    main.appendChild(section);
    renderRow(row, moviesInGenre(genre));
  });
}

// ---------------------------------------------------------------------
// RECOMMENDATIONS: each movie already stores its own precomputed
// top-12 list as {index, match} pairs pointing back into MOVIES.
// ---------------------------------------------------------------------
function showRecommendations(movie) {
  const recs = movie.recommendations || [];
  const matchLookup = new Map();
  const recMovies = recs.map((r) => {
    const m = MOVIES[r.index];
    matchLookup.set(m, r.match);
    return m;
  });

  const section = document.getElementById("recommendSection");
  document.getElementById("recommendTitle").textContent = `Because you liked "${movie.title}"`;
  renderRow(document.getElementById("recommendRow"), recMovies, matchLookup);

  section.classList.remove("hidden");
  section.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ---------------------------------------------------------------------
// SEARCH: filters the in-memory array directly, no network round trip
// ---------------------------------------------------------------------
function setupSearch() {
  const input = document.getElementById("searchInput");
  const resultsBox = document.getElementById("searchResults");

  input.addEventListener("input", () => {
    const query = input.value.trim().toLowerCase();

    if (!query) {
      resultsBox.classList.add("hidden");
      return;
    }

    const matches = MOVIES.filter((m) => m.title.toLowerCase().includes(query)).slice(0, 8);

    resultsBox.innerHTML = "";
    if (!matches.length) {
      resultsBox.classList.add("hidden");
      return;
    }

    matches.forEach((movie) => {
      const item = document.createElement("div");
      item.className = "search-result-item";
      item.innerHTML = `<span>${movie.title}</span><small>\u2605 ${movie.rating.toFixed(1)}</small>`;
      item.addEventListener("click", () => {
        resultsBox.classList.add("hidden");
        input.value = "";
        showRecommendations(movie);
      });
      resultsBox.appendChild(item);
    });

    resultsBox.classList.remove("hidden");
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".search-wrap")) resultsBox.classList.add("hidden");
  });
}

// ---------------------------------------------------------------------
// INIT
// ---------------------------------------------------------------------
(async function init() {
  await loadMovies();
  setupSearch();
  renderHero();
  renderGenreRows();
})();
