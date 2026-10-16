import os
import sqlite3
from datetime import datetime
from functools import wraps

import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-for-local-project")
DB_PATH = os.path.join(os.path.dirname(__file__), "movie_portal.db")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


SAMPLE_MOVIES = [
    ("The Conjuring", "Horror", 2013, "English", "Paranormal investigators help a family terrorized by a dark presence.", "paranormal haunted house supernatural family"),
    ("Insidious", "Horror", 2010, "English", "A family tries to save their son from a frightening supernatural world.", "paranormal supernatural family spirits"),
    ("A Quiet Place", "Horror", 2018, "English", "A family must stay silent to survive creatures that hunt by sound.", "creatures suspense family survival"),
    ("It", "Horror", 2017, "English", "A group of friends face a terrifying shape-shifting presence.", "clown supernatural friends mystery"),
    ("The Ring", "Horror", 2002, "English", "A journalist investigates a mysterious videotape linked to strange deaths.", "mystery supernatural curse"),
    ("Get Out", "Horror", 2017, "English", "A weekend visit turns disturbing as a young man uncovers a dark secret.", "psychological thriller mystery"),
    ("Interstellar", "Sci-Fi", 2014, "English", "Explorers travel through space in search of a future for humanity.", "space science future adventure"),
    ("Inception", "Sci-Fi", 2010, "English", "A skilled thief enters dreams to plant an idea in someone's mind.", "dreams science action thriller"),
    ("The Matrix", "Sci-Fi", 1999, "English", "A hacker discovers that reality is not what it seems.", "technology future action virtual reality"),
    ("Arrival", "Sci-Fi", 2016, "English", "A linguist tries to communicate with mysterious visitors from space.", "aliens language science mystery"),
    ("Dune", "Sci-Fi", 2021, "English", "A young noble travels to a dangerous desert planet with a valuable resource.", "space future adventure politics"),
    ("The Martian", "Sci-Fi", 2015, "English", "An astronaut stranded on Mars fights to survive and return home.", "space science survival"),
    ("The Dark Knight", "Action", 2008, "English", "A masked hero faces a dangerous criminal threatening a city.", "superhero crime action justice"),
    ("John Wick", "Action", 2014, "English", "A retired assassin returns to a dangerous underworld.", "assassin crime revenge fight"),
    ("Mad Max: Fury Road", "Action", 2015, "English", "Survivors cross a harsh desert in a high-speed chase.", "chase survival dystopian adventure"),
    ("Mission Impossible", "Action", 1996, "English", "A secret agent races to stop a dangerous conspiracy.", "spy mission thriller action"),
    ("The Hangover", "Comedy", 2009, "English", "Friends try to reconstruct a wild night before a wedding.", "friends funny mystery party"),
    ("3 Idiots", "Comedy", 2009, "Hindi", "Three college friends question pressure and expectations in education.", "college friends funny drama"),
    ("Home Alone", "Comedy", 1990, "English", "A child uses clever tricks to protect his home from burglars.", "family funny holiday"),
    ("Queen", "Comedy", 2014, "Hindi", "A young woman takes a solo trip and discovers her independence.", "travel friendship self discovery"),
    ("The Notebook", "Romance", 2004, "English", "Two young people fall in love despite differences and challenges.", "love relationship drama"),
    ("La La Land", "Romance", 2016, "English", "A musician and an actor pursue their dreams and relationship.", "music love dreams"),
    ("Titanic", "Romance", 1997, "English", "Two passengers from different backgrounds fall in love on a ship.", "love tragedy history"),
    ("Yeh Jawaani Hai Deewani", "Romance", 2013, "Hindi", "Friends explore travel, ambition, and relationships as they grow up.", "friendship travel love"),
    ("Drishyam", "Thriller", 2015, "Hindi", "A family man uses clever planning after a troubling incident.", "crime mystery family suspense"),
    ("Gone Girl", "Thriller", 2014, "English", "A disappearance turns into a media storm full of secrets.", "mystery crime psychological"),
    ("Knives Out", "Thriller", 2019, "English", "A detective investigates a suspicious death in a wealthy family.", "detective mystery crime"),
    ("Shutter Island", "Thriller", 2010, "English", "A detective investigates a disappearance at a remote institution.", "psychological mystery investigation"),
    ("Coco", "Animation", 2017, "English", "A young musician discovers family history in a colourful world.", "family music fantasy"),
    ("Inside Out", "Animation", 2015, "English", "Emotions guide a young girl through a major life change.", "family feelings adventure"),
]


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user'
    );
    CREATE TABLE IF NOT EXISTS movies (
        movie_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        genre TEXT NOT NULL,
        release_year INTEGER,
        language TEXT,
        description TEXT DEFAULT '',
        tags TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS ratings (
        rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        movie_id INTEGER NOT NULL,
        rating REAL NOT NULL CHECK(rating >= 1 AND rating <= 5),
        rated_at TEXT NOT NULL,
        UNIQUE(user_id, movie_id),
        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY(movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS recommendations (
        recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        movie_id INTEGER NOT NULL,
        score REAL NOT NULL,
        generated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY(movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE
    );
    """)
    count = db.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    if count == 0:
        db.executemany(
            "INSERT INTO movies(title,genre,release_year,language,description,tags) VALUES(?,?,?,?,?,?)",
            SAMPLE_MOVIES
        )
    db.commit()
    db.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Admin access only.", "danger")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


def movie_query(extra="", params=()):
    sql = """
    SELECT m.*, COALESCE(ROUND(AVG(r.rating), 2), 0) AS avg_rating,
           COUNT(r.rating_id) AS rating_count
    FROM movies m LEFT JOIN ratings r ON m.movie_id = r.movie_id
    """
    if extra:
        sql += " WHERE " + extra
    sql += " GROUP BY m.movie_id ORDER BY m.title"
    return get_db().execute(sql, params).fetchall()


def build_recommendations(user_id, limit=8):
    db = get_db()
    movies = db.execute("SELECT * FROM movies").fetchall()
    if not movies:
        return []
    ratings = db.execute(
        "SELECT movie_id, rating FROM ratings WHERE user_id = ?", (user_id,)
    ).fetchall()
    rated_ids = {r["movie_id"] for r in ratings}

    # TF-IDF compares genre, tags, and description to find similar movies.
    texts = [
        f'{m["title"]} {m["genre"]} {m["tags"] or ""} {m["description"] or ""} {m["language"] or ""}'
        for m in movies
    ]
    matrix = TfidfVectorizer(stop_words="english").fit_transform(texts)
    similarity = cosine_similarity(matrix)

    index_by_id = {m["movie_id"]: i for i, m in enumerate(movies)}
    global_ratings = db.execute("""
        SELECT movie_id, AVG(rating) AS avg_rating, COUNT(*) AS n
        FROM ratings GROUP BY movie_id
    """).fetchall()
    stats = {row["movie_id"]: row for row in global_ratings}

    # A user's movies rated 4 or 5 are positive examples; low-rated movies are negative.
    positive = [r for r in ratings if r["rating"] >= 4]
    negative = [r for r in ratings if r["rating"] <= 2]
    scored = []
    for movie in movies:
        mid = movie["movie_id"]
        if mid in rated_ids:
            continue
        idx = index_by_id[mid]
        score = 0.0
        weight_sum = 0.0
        for r in positive:
            sim = similarity[idx, index_by_id[r["movie_id"]]]
            weight = max(0.1, r["rating"] - 3)
            score += sim * weight
            weight_sum += weight
        if weight_sum:
            score = score / weight_sum
        for r in negative:
            score -= 0.25 * similarity[idx, index_by_id[r["movie_id"]]]
        stat = stats.get(mid)
        avg = float(stat["avg_rating"]) if stat and stat["avg_rating"] else 3.5
        n = int(stat["n"]) if stat else 0
        # Add a small popularity/rating signal; content similarity remains the main score.
        score += (avg / 5.0) * 0.12 + min(n, 10) * 0.003
        scored.append((movie, round(score, 4)))

    scored.sort(key=lambda item: item[1], reverse=True)
    now = datetime.now().isoformat(timespec="seconds")
    db.execute("DELETE FROM recommendations WHERE user_id = ?", (user_id,))
    for movie, score in scored[:limit]:
        db.execute(
            "INSERT INTO recommendations(user_id,movie_id,score,generated_at) VALUES(?,?,?,?)",
            (user_id, movie["movie_id"], score, now)
        )
    db.commit()

    result = []
    for movie, score in scored[:limit]:
        result.append({**dict(movie), "score": score})
    return result


@app.route("/")
def index():
    top_movies = get_db().execute("""
        SELECT m.*, COALESCE(ROUND(AVG(r.rating),2),0) AS avg_rating,
        COUNT(r.rating_id) AS rating_count
        FROM movies m LEFT JOIN ratings r ON m.movie_id=r.movie_id
        GROUP BY m.movie_id ORDER BY avg_rating DESC, rating_count DESC LIMIT 6
    """).fetchall()
    return render_template("index.html", top_movies=top_movies)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 6:
            flash("Enter your name and email, and use a password with at least 6 characters.", "danger")
            return redirect(url_for("register"))
        try:
            get_db().execute(
                "INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                (name, email, generate_password_hash(password))
            )
            get_db().commit()
            flash("Account created. Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("That email is already registered.", "danger")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["user_id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            flash("Welcome back!", "success")
            return redirect(url_for("dashboard"))
        flash("Incorrect email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You are logged out.", "info")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    user_ratings = db.execute("""
        SELECT m.title, m.genre, r.rating, r.rated_at
        FROM ratings r JOIN movies m ON m.movie_id=r.movie_id
        WHERE r.user_id=? ORDER BY r.rated_at DESC
    """, (session["user_id"],)).fetchall()
    recommendations = build_recommendations(session["user_id"], 5)
    return render_template("dashboard.html", user_ratings=user_ratings, recommendations=recommendations)


@app.route("/movies")
def movies():
    search = request.args.get("q", "").strip()
    genre = request.args.get("genre", "").strip()
    language = request.args.get("language", "").strip()
    filters, params = [], []
    if search:
        filters.append("(m.title LIKE ? OR m.description LIKE ? OR m.tags LIKE ?)")
        params.extend([f"%{search}%"] * 3)
    if genre:
        filters.append("m.genre = ?")
        params.append(genre)
    if language:
        filters.append("m.language = ?")
        params.append(language)
    rows = movie_query(" AND ".join(filters), tuple(params))
    genres = [r["genre"] for r in get_db().execute("SELECT DISTINCT genre FROM movies ORDER BY genre")]
    languages = [r["language"] for r in get_db().execute("SELECT DISTINCT language FROM movies WHERE language IS NOT NULL ORDER BY language")]
    my_ratings = {}
    if session.get("user_id"):
        my_ratings = {
            row["movie_id"]: row["rating"] for row in get_db().execute(
                "SELECT movie_id,rating FROM ratings WHERE user_id=?", (session["user_id"],)
            )
        }
    return render_template("movies.html", movies=rows, genres=genres, languages=languages,
                           selected_genre=genre, selected_language=language, q=search, my_ratings=my_ratings)


@app.route("/rate/<int:movie_id>", methods=["POST"])
@login_required
def rate_movie(movie_id):
    try:
        rating = float(request.form.get("rating", "0"))
    except ValueError:
        rating = 0
    exists = get_db().execute("SELECT movie_id FROM movies WHERE movie_id=?", (movie_id,)).fetchone()
    if not exists or not (1 <= rating <= 5):
        flash("Please choose a rating from 1 to 5.", "danger")
        return redirect(request.referrer or url_for("movies"))
    get_db().execute("""
        INSERT INTO ratings(user_id,movie_id,rating,rated_at) VALUES(?,?,?,?)
        ON CONFLICT(user_id,movie_id) DO UPDATE SET rating=excluded.rating, rated_at=excluded.rated_at
    """, (session["user_id"], movie_id, rating, datetime.now().isoformat(timespec="seconds")))
    get_db().commit()
    flash("Your rating has been saved.", "success")
    return redirect(request.referrer or url_for("movies"))


@app.route("/recommendations")
@login_required
def recommendations():
    rows = build_recommendations(session["user_id"], 12)
    return render_template("recommendations.html", recommendations=rows)


@app.route("/analytics")
def analytics():
    db = get_db()
    rating_rows = db.execute("""
        SELECT m.title, m.genre, m.language, r.rating
        FROM ratings r JOIN movies m ON m.movie_id=r.movie_id
    """).fetchall()
    movie_rows = db.execute("SELECT * FROM movies").fetchall()
    ratings_df = pd.DataFrame([dict(r) for r in rating_rows])
    movies_df = pd.DataFrame([dict(m) for m in movie_rows])

    if ratings_df.empty:
        top_movies = []
        genre_data = []
        rating_distribution = [{"rating": i, "count": 0} for i in range(1, 6)]
        genre_labels, genre_values = [], []
    else:
        top_movies = (
            ratings_df.groupby(["title", "genre"], as_index=False)
            .agg(avg_rating=("rating", "mean"), rating_count=("rating", "count"))
            .sort_values(["avg_rating", "rating_count"], ascending=False)
            .head(10).to_dict("records")
        )
        genre_stats = ratings_df.groupby("genre", as_index=False).agg(
            rating_count=("rating", "count"), average_rating=("rating", "mean")
        ).sort_values("rating_count", ascending=False)
        genre_data = genre_stats.to_dict("records")
        genre_labels = genre_stats["genre"].tolist()
        genre_values = genre_stats["rating_count"].astype(int).tolist()
        rating_distribution = []
        for i in range(1, 6):
            count = int((ratings_df["rating"].round() == i).sum())
            rating_distribution.append({"rating": i, "count": count})

    total_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_movies = db.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    total_ratings = db.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
    return render_template("analytics.html", top_movies=top_movies, genre_data=genre_data,
                           rating_distribution=rating_distribution, genre_labels=genre_labels,
                           genre_values=genre_values, total_users=total_users,
                           total_movies=total_movies, total_ratings=total_ratings)


@app.route("/admin")
@admin_required
def admin():
    db = get_db()
    all_movies = db.execute("SELECT * FROM movies ORDER BY title").fetchall()
    users = db.execute("SELECT user_id,name,email,role FROM users ORDER BY user_id DESC").fetchall()
    return render_template("admin.html", movies=all_movies, users=users)


@app.route("/admin/add-movie", methods=["POST"])
@admin_required
def add_movie():
    title = request.form.get("title", "").strip()
    genre = request.form.get("genre", "").strip()
    year = request.form.get("release_year", "").strip()
    language = request.form.get("language", "").strip()
    description = request.form.get("description", "").strip()
    tags = request.form.get("tags", "").strip()
    if not title or not genre:
        flash("Movie title and genre are required.", "danger")
    else:
        try:
            year_value = int(year) if year else None
            get_db().execute(
                "INSERT INTO movies(title,genre,release_year,language,description,tags) VALUES(?,?,?,?,?,?)",
                (title, genre, year_value, language, description, tags)
            )
            get_db().commit()
            flash("Movie added successfully.", "success")
        except ValueError:
            flash("Release year must be a number.", "danger")
    return redirect(url_for("admin"))


@app.route("/admin/delete-movie/<int:movie_id>", methods=["POST"])
@admin_required
def delete_movie(movie_id):
    get_db().execute("DELETE FROM movies WHERE movie_id=?", (movie_id,))
    get_db().commit()
    flash("Movie deleted.", "info")
    return redirect(url_for("admin"))


@app.route("/admin/make-admin/<int:user_id>", methods=["POST"])
@admin_required
def make_admin(user_id):
    get_db().execute("UPDATE users SET role='admin' WHERE user_id=?", (user_id,))
    get_db().commit()
    flash("User role updated to admin.", "success")
    return redirect(url_for("admin"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
